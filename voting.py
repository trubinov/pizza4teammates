import random
import json
import string
from os import mkdir
from os.path import dirname, exists, join
from pizzburg import PizzburgParser


class VotingData:
    """
    Реализация методов голосования
    """
    RESULT_PATH = join(dirname(__file__), 'data', 'voting_results')

    def __init__(self, parser, amount, dia, h):
        self.parser = parser
        self.amount = amount
        self.menu = self._load_menu(dia, h)
        self.votes = dict()
        self.voters = dict()
        self.order_ids = list()

    def _load_menu(self, dia, h):
        _menu = list()
        for item in self.parser.menu:
            title = item.get('title')
            info = item.get('info')
            for v in item.get('variants'):
                if v.get('dia') == dia and v.get('h') == h:
                    _menu.append((title, v.get('price'), info, item.get('hot')))
        return _menu

    def vote_for_pizza(self, user_id, user_name, pizza_id):
        if user_id not in self.votes:
            self.votes[user_id] = list()
        if pizza_id in self.votes[user_id]:
            return 1
        if len(self.votes[user_id]) >= self.amount:
            return 2
        self.votes[user_id].append(pizza_id)
        self.voters[user_id] = user_name
        return 0

    def calc_result(self):
        persons = len(self.votes)
        if persons <= 0:
            return False
        # словарь pizza_id: количество голосов
        result = dict()
        for user_id in self.votes:
            for pizza_id in self.votes[user_id]:
                if pizza_id not in result:
                    result[pizza_id] = 0
                result[pizza_id] += 1
        # развернём данные и посчитаем по количеству голосов
        rating = dict()
        for pizza_id in result:
            vote_amount = result[pizza_id]
            if vote_amount in rating:
                rating[vote_amount].append(pizza_id)
            else:
                rating[vote_amount] = [pizza_id]
        sorted_rating = sorted(rating, reverse=True)
        # получили отсортированный рейтинг - набираем пиццы в результат
        self.order_ids.clear()
        for vote_amount in sorted_rating:
            left_to_add = self.amount - len(self.order_ids)
            if left_to_add <= 0:
                break
            pizzas = rating[vote_amount]
            pizzas_amount = len(pizzas)
            if pizzas_amount <= left_to_add:
                pizzas_to_add = pizzas
            else:
                pizzas_to_add = random.sample(pizzas, k=min(left_to_add, pizzas_amount))
            self.order_ids.extend(pizzas_to_add)
        order = [f'({result[p]})\t{self.menu[p][0]}' for p in self.order_ids]
        order_sum = sum(map(lambda p: self.menu[p][1], self.order_ids))
        return {
            'order': order,
            'sum': order_sum,
            'votes_amount': persons,
            'sum_for_person': round(order_sum / persons, 2),
            'pie_for_person': round(8 * len(order) / persons, 2)
        }

    def dump_results(self, total_results, filename_suffix=''):
        by_users = list()
        for k, v in self.votes.items():
            by_users.append({
                'username': self.voters[k],
                'choice': [self.menu[x][0] for x in v]
            })
        if not exists(VotingData.RESULT_PATH):
            mkdir(VotingData.RESULT_PATH)
        result_file_name = ''.join(random.choice(string.ascii_letters) for _ in range(10)) + filename_suffix + '.json'
        with open(join(VotingData.RESULT_PATH, result_file_name), 'w', encoding='utf-8') as result_file:
            file_data = dict()
            file_data['total'] = total_results
            file_data['by_users'] = by_users
            json.dump(file_data, result_file, indent=4, ensure_ascii=False)

    def user_result(self, user_id):
        if user_id in self.votes:
            return [self.menu[x][0] for x in self.votes[user_id]]
        return None

    @property
    def voters_list(self):
        return self.voters.values()

    @property
    def menu_url(self):
        return self.parser.MENU_URL

    def get_voters_list(self):

        def intersection_percent(l1, l2):
            return round(len([x for x in l1 if x in l2]) / len(l2) * 100, 2)

        voters_list = list()
        for user_id, user_name in self.voters.items():
            voters_list.append({
                'user_id': user_id,
                'user_name': user_name,
                'satisfaction': intersection_percent(self.votes[user_id], self.order_ids)
            })
        return voters_list


if __name__ == '__main__':
    parser = PizzburgParser(reload_from_site=True)
    vote_data = VotingData(parser, 5, 32, 'пышное')
    print(f'Голосование запущено. Полное меню здесь: {vote_data.menu_url}')

    votes = [
        [1, 2, 3, 4, 5],
        [2, 3, 8, 5, 6],
        [1, 2, 3, 4, 6],
        [0, 8]
    ]
    for u_id, vote in enumerate(votes):
        for p_id in vote:
            vote_data.vote_for_pizza(u_id, f'NoName{p_id}', p_id)

    res = vote_data.calc_result()
    vote_data.dump_results(res, '_test')
    order_list = '\n'.join(res['order'])
    print(f"Проголосовало человек: {res['votes_amount']}\n"
          f"Ваш заказ: \n{order_list}\nна сумму {res['sum']} руб.\n"
          f"Это по {res['sum_for_person']} руб. с человека, и по {res['pie_for_person']} кусков.")

    by_persons = vote_data.get_voters_list()
    for item in by_persons:
        print(item)
