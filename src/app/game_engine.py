from src.Globals import Constants as Consts
from src.app.models import get_tasks_info, update_tasks_info


class GameEngine:
    def create_tasks_for_render(self):
        self.tasks = dict()
        for key in Consts.TASKS_KEYS[self.game.game_type]:
            position = Consts.TASKS_POSITIONS_BY_KEYS[self.game.type][key]
            self.tasks[key] = {'id': self.tasks_positions[position].id,
                               'name': position,
                               'state': self.tasks_states[key]}
        return self.tasks

    def create_picked_tasks(self):
        self.keys_of_picked_tasks = self.tasks_states['picked_tasks']
        self.picked_tasks = []
        for key in self.keys_of_picked_tasks:
            position = Consts.TASKS_POSITIONS_BY_KEYS[self.game.type][key]
            self.picked_tasks.append(
                {'id': self.tasks_positions[position].id,
                 'name': position,
                 'state': self.tasks_states[key],
                 'condition': self.tasks_positions[position].condition})

    def __init__(self, game, team):
        self.game = game
        self.team = team
        self.tasks_positions = game.tasks_positions_for_render
        self.tasks_states = get_tasks_info('states', game.id, login=team.login)
        self.numbers_of_sets = get_tasks_info('numbers_of_sets', game.id)
        self.tasks = None
        self.create_tasks_for_render()
        self.message = None
        self.picked_tasks = None
        self.keys_of_picked_tasks = None
        self.create_picked_tasks()

    def get_info(self):
        result = {"tasks": self.tasks,
                  "picked_tasks": self.picked_tasks,
                  "message": self.message,
                  "number_of_picked_tasks": len(self.picked_tasks),
                  "info": self.numbers_of_sets}
        return result


def get_state(state):
    return state[-2:]


class DominoEngine(GameEngine):
    def set_states(self):
        for key in Consts.TASKS_KEYS['domino']:
            if get_state(self.tasks[key]['state']) == 'ok' and \
                    self.numbers_of_sets[key]['number_of_sets'] == 0:
                self.tasks[key]['state'] = '0bo'
            elif get_state(self.tasks[key]['state']) == 'ff' and \
                    self.numbers_of_sets[key]['number_of_sets'] == 0:
                self.tasks[key]['state'] = '0bf'
            elif get_state(self.tasks[key]['state']) == 'bo' and \
                    self.numbers_of_sets[key]['number_of_sets'] > 0:
                self.tasks[key]['state'] = '0ok'
            elif get_state(self.tasks[key]['state']) == 'bf' and \
                    self.numbers_of_sets[key]['number_of_sets'] > 0:
                self.tasks[key]['state'] = '0ff'

    def pick_task(self, task_name):
        key = Consts.TASKS_KEYS_BY_POSITIONS[self.game.type][task_name]
        number_of_picked_task = len(self.picked_tasks)
        changes_numbers_of_sets = dict()
        changes_tasks_states = dict()
        if number_of_picked_task == Consts.MAX_TASKS_IN_HAND[self.game.type]:
            self.message = Consts.MESSAGES[self.game.type]['full']
        elif key in self.keys_of_picked_tasks:
            self.message = Consts.MESSAGES[self.game.type]['full']
        elif get_state(self.tasks[key]['state']) in ['ff', 'ok']:
            self.keys_of_picked_tasks.append(key)
            changes_tasks_states['picked_tasks'] = ' '.join(
                self.keys_of_picked_tasks)
            task_position = Consts.TASKS_POSITIONS_BY_KEYS[self.game.type][key]
            new_task = {'id': self.tasks_positions[task_position].id,
                        'name': task_position,
                        'state': self.tasks_states[key],
                        'condition':
                            self.tasks_positions[task_position].condition}
            self.picked_tasks.append(new_task)
            if key not in changes_numbers_of_sets.keys():
                changes_numbers_of_sets[key] = dict()
            changes_numbers_of_sets[key]['number_of_sets'] = \
                self.numbers_of_sets[key]['number_of_sets'] - 1
        else:
            self.message = Consts.MESSAGES['domino'][get_state(self.tasks[key][
                                                                   'state'])]
        update_tasks_info('states', self.game.id, changes_tasks_states,
                          login=self.team.login)
        update_tasks_info('numbers_of_sets', self.game.id,
                          changes_numbers_of_sets)

    def task_points(self, key):
        return map(int, self.tasks[key]['name'].split('-'))

    def handle_answer(self, task_name, answer):
        key = Consts.TASKS_KEYS_BY_POSITIONS[self.game.type][task_name]
        task = self.tasks_positions[Consts.TASKS_POSITIONS_BY_KEYS[
            self.game.type][key]]
        verdicts = ['ok', 'ff', 'fs']
        name = self.tasks[key]['name']
        state = self.tasks[key]['state']
        changes_tasks_states = dict()
        changes_numbers_of_sets = dict()
        sets = self.numbers_of_sets[key]['number_of_sets']
        formatted_state = get_state(state)
        tasks_points = self.task_points(key)
        if formatted_state in ['ok', 'ff'] and key in self.keys_of_picked_tasks:
            result = task.check_ans(answer)
            if result and formatted_state == 'ok':
                state = str(sum(tasks_points)) + 'af'
                if name == '0-0':
                    state = '10af'
            elif result:
                state = str(max(tasks_points)) + 'as'
            else:
                state = verdicts[verdicts.index(formatted_state) + 1]
                if state == 'ff':
                    state = '0ff'
                else:
                    state = str(-min(tasks_points)) + 'fs'
                if name == '0-0':
                    state = '0fs'
            self.tasks[key]['state'] = state
            self.keys_of_picked_tasks.remove(key)
            self.picked_tasks = []
            changes_tasks_states['picked_tasks'] = ' '.join(
                self.keys_of_picked_tasks)
            changes_tasks_states[key] = state
            for key in self.keys_of_picked_tasks:
                position = Consts.TASKS_POSITIONS_BY_KEYS['domino'][key]
                self.picked_tasks.append(
                    {'name': position,
                     'condition': self.tasks_positions[position].condition})
            if key not in changes_numbers_of_sets.keys():
                changes_numbers_of_sets[key] = dict()
            changes_numbers_of_sets[key]['number_of_sets'] = sets + 1
        update_tasks_info('states', self.game.id, changes_tasks_states,
                          login=self.team.login)
        update_tasks_info('numbers_of_sets', self.game.id,
                          changes_numbers_of_sets)

    def __init__(self, game, team):
        super().__init__(game, team)
        self.set_states()


class PenaltyEngine(GameEngine):
    def handle_answer(self, task_name, answer):
        key = Consts.TASKS_KEYS_BY_POSITIONS['penalty'][task_name]
        task = self.tasks_positions[Consts.TASKS_POSITIONS_BY_KEYS['penalty'][
            key]]
        state = self.tasks[key]['state']
        sets = self.numbers_of_sets[key]['number_of_sets']
        formatted_state = get_state(state)
        result = task.check_ans(answer)
        changes_numbers_of_sets = dict()
        changes_tasks_states = dict()
        verdicts = ['ok', 'ff', 'fs']
        cost = self.numbers_of_sets[key]['cost']
        if result:
            if formatted_state == 'ok':
                state = str(cost) + 'af'
                if key not in changes_numbers_of_sets.keys():
                    changes_numbers_of_sets[key] = dict()
                changes_numbers_of_sets[key]['number_of_sets'] = sets - 1
                if cost > 5:
                    if changes_numbers_of_sets[key]['number_of_sets'] == 0:
                        changes_numbers_of_sets[key]['cost'] = cost - 1
                        changes_numbers_of_sets[key]['number_of_sets'] = \
                            self.game.sets_number
            else:
                state = '3' + 'as'
        else:
            state = verdicts[verdicts.index(get_state(state)) + 1]
            if state == 'ff':
                state = '0' + 'ff'
            else:
                state = '-2' + 'fs'
        changes_tasks_states[key] = state
        update_tasks_info('states', self.game.id, changes_tasks_states,
                          login=self.team.login)
        update_tasks_info('numbers_of_sets', self.game.id,
                          changes_numbers_of_sets)

    def __init__(self, game, team):
        super().__init__(game, team)


def create_engine(game, team):
    result = None
    if game.game_type == "domino":
        result = DominoEngine(game, team)
    elif game.game_type == "penalty":
        result = PenaltyEngine(game, team)
    return result
