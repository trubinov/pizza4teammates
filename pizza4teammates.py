from os import getenv
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.utils.exceptions import MessageNotModified
from voting import VotingData
from pizzburg import PizzburgParser


async def new_voting(message: types.Message):
    amount = 5
    d = 32
    h = 'пышное'
    msg_parts = message.text.split(' ')
    if len(msg_parts) > 1 and msg_parts[1].isdigit():
        amount = int(msg_parts[1])
    if len(msg_parts) > 2 and msg_parts[2].isdigit():
        d = int(msg_parts[2])
    if len(msg_parts) > 3:
        h = msg_parts[3]
    pp = PizzburgParser(reload_from_site=True)
    v = VotingData(pp, amount, d, h)
    message.bot['voting'] = v
    kbd_items = [InlineKeyboardButton(item[0], callback_data=str(k)) for k, item in enumerate(v.menu)]
    kbd = InlineKeyboardMarkup()
    kbd.add(*kbd_items)
    kbd.add(InlineKeyboardButton('Посмотреть мой выбор...', callback_data="my_choice"))
    v_msg = await message.answer(f'Голосование запущено!\n'
                                 f'Полное меню здесь: {v.menu_url}\n'
                                 f'А сейчас выберите {amount} пицц из списка ниже:', reply_markup=kbd)
    message.bot['voting_message_id'] = v_msg.message_id
    res_msg = await message.answer('Голосуем, дамы и господа!')
    message.bot['voting_res_message_id'] = res_msg.message_id


async def vote_for_pizza(query: CallbackQuery):
    if 'voting' not in query.bot:
        await query.answer('Голосование не запущено, попробуйте позже!')
        return
    v = query.bot['voting']
    if not isinstance(v, VotingData):
        await query.answer('Голосование не запущено, попробуйте позже!')
        return
    if not query.data.isdigit():
        your_choice = v.user_result(query.from_user.id)
        if your_choice:
            await query.answer(f"Ваш выбор: \n{', '.join(your_choice)}", show_alert=True)
        else:
            await query.answer(f"Вы ещё не голосовали!")
        return
    pizza_id = int(query.data)
    vote_accepted = v.vote_for_pizza(query.from_user.id, query.from_user.full_name, pizza_id)
    if vote_accepted == 0:
        await query.answer('Спасибо, Ваш голос учтен!')
        if query.bot['voting_res_message_id']:
            end_voting = len([1 for x in v.votes if len(v.votes[x]) == v.amount])
            new_text = f'Проголосовало участников: {len(v.votes)}\n' \
                       f'Завершило голосование: {end_voting}'
            try:
                await query.bot.edit_message_text(new_text, query.message.chat.id, query.bot['voting_res_message_id'])
            except MessageNotModified:
                pass
    elif vote_accepted == 1:
        await query.answer('Извините, 1 пицца - 1 ваш голос!')
    elif vote_accepted == 2:
        your_choice = v.user_result(query.from_user.id)
        await query.answer(f"Вы уже сделали свой выбор.\nВаш набор: \n{', '.join(your_choice)}", show_alert=True)
    return


async def finish_voting(message: types.Message):
    v = message.bot['voting']
    if isinstance(v, VotingData):
        if message.bot['voting_message_id']:
            await message.bot.delete_message(message.chat.id, message.bot['voting_message_id'])
        voting_result = v.calc_result()
        if not voting_result:
            await message.answer('Голосование не состоялось, данных недостаточно!')
            return
        v.dump_results(voting_result)
        pizzas_list = '\n'.join(voting_result['order'])
        voters_list = '\n'.join([f"{x['user_name']} ({x['satisfaction']})" for x in v.get_voters_list()])
        result_text = f"\U0001F355 Голосование окончено! \U0001F355\n\n"\
                      f"Проголосовало человек: {voting_result['votes_amount']}\n"\
                      f"Ваш заказ:\n{pizzas_list}\nна сумму {voting_result['sum']} руб.\n"\
                      f"Это по {voting_result['sum_for_person']} руб. с человека, "\
                      f"и по {voting_result['pie_for_person']} кусков \U0001F355.\n" \
                      f"В голосовании приняли участие:\n" \
                      f"{voters_list}\n\n" \
                      f"В скобках указан процент совпадения заказа участника голосования с итоговым заказом."
        await message.answer(result_text)
        message.bot['voting'] = None
        message.bot['voting_message_id'] = None
        message.bot['voting_res_message_id'] = None
        return
    await message.answer('Голосование не запущено, попробуйте позже!')


if __name__ == '__main__':
    bot = Bot(getenv('BOT_TOKEN'))
    dp = Dispatcher(bot)
    dp.register_message_handler(new_voting, commands=['pizza'])
    dp.register_callback_query_handler(vote_for_pizza)
    dp.register_message_handler(finish_voting, commands=['finish'])
    executor.start_polling(dp)
