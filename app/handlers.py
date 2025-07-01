from database.init_database import AsyncSessionLocal
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, update, delete
from database.models import Users, Teams, UserTeam, Tasks
from app.keyboards import start_kb, admin_kb, back_kb
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import random
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime


router_handlers = Router()


@router_handlers.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Users).where(Users.user_id == user_id))
        user = result.scalar()

        if user:
            await message.reply("Снова добро пожаловать!", reply_markup=start_kb)
        else:
            await message.reply("Добро пожаловать!", reply_markup=start_kb)
            session.add(Users(user_id=user_id, user_name=user_name))
            await session.commit()


class CreateTeamState(StatesGroup):
    waiting_for_name = State()
    waiting_for_join_key = State()


@router_handlers.message(F.text == "Создать команду")
async def handle_create_team(message: Message, state: FSMContext):
    await message.answer("Введите название команды:")
    await state.set_state(CreateTeamState.waiting_for_name)


@router_handlers.message(CreateTeamState.waiting_for_name)
async def process_team_name(message: Message, state: FSMContext):
    team_name = message.text.strip()
    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(Teams).where(Teams.team_name == team_name)
        )
        if existing.scalar():
            await message.answer("❗ Команда с таким названием уже существует. Попробуйте другое.")
            return

        team_id = random.randint(100000, 999999)
        new_team = Teams(team_name=team_name, admin_id=user_id, team_id=team_id, join_key=random.randint(1000000, 9999999))
        user_team = UserTeam(user_id=user_id, team_name=team_name)
        session.add(new_team)
        session.add(user_team)
        await session.commit()

        await message.answer(f"✅ Команда \"{team_name}\" успешно создана!")
        await state.clear()


@router_handlers.message(F.text == "Войти в команду")
async def handle_create_team(message: Message, state: FSMContext):
    await message.answer("Введите ключ:")
    await state.set_state(CreateTeamState.waiting_for_join_key)


@router_handlers.message(CreateTeamState.waiting_for_join_key)
async def process_team_name(message: Message, state: FSMContext):
    try:
        join_key = int(message.text.strip())
    except ValueError:
        await message.answer("Данный ключ не соответсвует формату")
        await state.clear()
        return
    target_user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Teams).where(Teams.join_key == join_key)
        )
        team = result.scalar()
        if team:
            check = await session.execute(
                select(UserTeam).where(UserTeam.user_id == target_user_id and UserTeam.team_name == team.team_name)
            )
            c = check.scalar()
            if c is None:
                user_team = UserTeam(user_id=target_user_id, team_name=team.team_name)
                session.add(user_team)
                await session.commit()

                await message.answer(f"✅ Вы добавлены в команду {team.team_name}!")
                await state.clear()
            else:
                await message.answer("Вы уже в команде")
        else:
            await message.answer("Данного ключа нет")
            await state.clear()


@router_handlers.message(F.text == "Мои команды")
async def my_teams(message: Message):
    user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            UserTeam.__table__.select().where(UserTeam.user_id == user_id)
        )
        commands = result.fetchall()

    if not commands:
        await message.answer("У тебя пока нет команд.")
        return

    buttons = [
        [InlineKeyboardButton(text=row.team_name, callback_data=f"cmd_{row.team_name}")]
        for row in commands
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer("Твои команды:", reply_markup=keyboard)


@router_handlers.callback_query(F.data.startswith("cmd_"))
async def show_command(callback: CallbackQuery):
    team_name = callback.data.split("_")[1]
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        task_result = await session.execute(
            select(Tasks).where(Tasks.team_name == team_name and Tasks.user_id == user_id)
        )
        admin_check = await session.execute(
            select(Teams).where(Teams.admin_id == user_id)
        )

        await session.execute(
            update(Users)
            .where(Users.user_id == user_id)
            .values(current_team=team_name)
        )
        await session.commit()
        admin_panel = admin_check.scalar()
        tasks = task_result.scalars().all()

        if admin_panel:
            userteam_result = await session.execute(
                select(UserTeam).where(UserTeam.team_name == team_name)
            )
            user_teams = userteam_result.scalars().all()
            user_ids = [ut.user_id for ut in user_teams]
            users_result = await session.execute(
                select(Users).where(Users.user_id.in_(user_ids))
            )
            users = users_result.scalars().all()

            text = f"*Участники команды* _{team_name}_:\n\n"
            for user in users:
                text += f"• {user.user_name or 'Без имени'} — `{user.user_id}`\n"
            text += f"\n🔑 *Ключ команды:* `{admin_panel.join_key}`"
            await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_kb)
        else:
            if tasks:
                text = "📋 *Ваши задания:*\n\n"
                for row in tasks:
                    text += f"• {row.description} — _{row.deadline}_\n"
                await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_kb)
            else:
                await callback.message.edit_text("У вас пока нет заданий", reply_markup=back_kb)


@router_handlers.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            UserTeam.__table__.select().where(UserTeam.user_id == user_id)
        )
        commands = result.fetchall()

    buttons = [
        [InlineKeyboardButton(text=row.team_name, callback_data=f"cmd_{row.team_name}")]
        for row in commands
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("Твои команды:", reply_markup=keyboard)


class TaskAssignFSM(StatesGroup):
    waiting_user_id = State()
    waiting_description = State()
    waiting_deadline = State()


@router_handlers.callback_query(F.data == "give_task")
async def start_task_assignment(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите Telegram ID пользователя, которому хотите назначить задачу:")
    await state.set_state(TaskAssignFSM.waiting_user_id)


@router_handlers.message(TaskAssignFSM.waiting_user_id)
async def get_user_id(message: Message, state: FSMContext):
    try:
        target_user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректный числовой ID пользователя.")
        return

    assigner_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Users).where(Users.user_id == assigner_id))
        assigner = result.scalar_one_or_none()

        team_name = assigner.current_team

        check = await session.execute(
            select(UserTeam).where(
                UserTeam.team_name == team_name,
                UserTeam.user_id == target_user_id
            )
        )
        is_member = check.scalar_one_or_none()

        if not is_member:
            await message.answer("❌ Указанный пользователь не состоит в вашей текущей команде.")
            await state.clear()
            return

        await state.update_data(target_user_id=target_user_id, team_name=team_name)
        await message.answer("Введите описание задачи:")
        await state.set_state(TaskAssignFSM.waiting_description)


@router_handlers.message(TaskAssignFSM.waiting_description)
async def get_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await message.answer("Введите дедлайн задачи (например, 2025-06-20):")
    await state.set_state(TaskAssignFSM.waiting_deadline)


@router_handlers.message(TaskAssignFSM.waiting_deadline)
async def save_task(message: Message, state: FSMContext):
    deadline_str = message.text.strip()

    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте формат: ГГГГ-ММ-ДД (например: 2025-06-20).")
        return

    data = await state.get_data()

    task = Tasks(
        team_name=data["team_name"],
        user_id=data["target_user_id"],
        description=data["description"],
        deadline=deadline_str
    )

    async with AsyncSessionLocal() as session:
        session.add(task)
        await session.commit()

    await message.answer("✅ Задача успешно добавлена.")
    await state.clear()


@router_handlers.callback_query(F.data == "delete_team")
async def delete_team(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        cur_team = await session.execute(
            select(Users).where(Users.user_id == user_id)
        )
        current_team = cur_team.scalar()
        await session.execute(
            delete(UserTeam).where(UserTeam.team_name == current_team.current_team)
        )
        await session.execute(
            delete(Tasks).where(Tasks.team_name == current_team.current_team)
        )
        await session.execute(
            delete(Teams).where(Teams.team_name == current_team.current_team and Teams.admin_id == user_id)
        )
        await session.commit()
        await callback.message.answer("Команда удалена!")


class DeleteMemberFSM(StatesGroup):
    waiting_user_id = State()


@router_handlers.callback_query(F.data == "delete_member")
async def delete_member(callback: Message, state: FSMContext):
    await callback.message.answer("Введите Telegram ID пользователя:")
    await state.set_state(DeleteMemberFSM.waiting_user_id)


@router_handlers.message(DeleteMemberFSM.waiting_user_id)
async def get_member_user_id(message: Message, state: FSMContext):
    try:
        target_user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректный числовой ID пользователя.")
        return

    await state.update_data(user_id=target_user_id)
    data = await state.get_data()
    user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        cur_team = await session.execute(
            select(Users).where(Users.user_id == user_id)
        )
        current_team = cur_team.scalar()
        check = await session.execute(
            select(UserTeam).where(UserTeam.user_id == target_user_id and UserTeam.team_name == current_team.current_team)
        )
        if check is not None:
            await session.execute(
                delete(UserTeam).where(UserTeam.user_id == int(data["user_id"]) and UserTeam.team_name == current_team.current_team)
            )
            await session.execute(
                delete(Tasks).where(Tasks.team_name == current_team.current_team and UserTeam.user_id == int(data["user_id"]))
            )
            await session.commit()
            await message.answer("Участник удалён!")
        else:
            await message.answer("В Вашей комаде нет указанного участника")

