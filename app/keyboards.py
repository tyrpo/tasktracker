from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardButton, InlineKeyboardMarkup)

start_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Мои команды')],
    [KeyboardButton(text='Создать команду'), KeyboardButton(text='Войти в команду')]
], resize_keyboard=True, one_time_keyboard=True)
admin_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Дать задание", callback_data="give_task")],
    [InlineKeyboardButton(text="Удалить участника", callback_data="delete_member")],
    [InlineKeyboardButton(text="Удалить команду", callback_data="delete_team")],
    [InlineKeyboardButton(text="Назад", callback_data="back")]
])
back_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Назад", callback_data="back")]
])
