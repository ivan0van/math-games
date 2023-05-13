import os
from datetime import datetime
import sys

import sqlalchemy as sql
from flask_login import UserMixin
from flask_sqlalchemy import orm
from werkzeug.security import generate_password_hash, check_password_hash
from src.app import db
from src.Globals import basedir, Config, Constants as Consts

db.metadata.clear()

authors_to_games_assoc_table = db.Table(
    'authors_to_games', db.metadata,
    db.Column('authoring_game', db.ForeignKey('games.id'), primary_key=True),
    db.Column('author', db.ForeignKey('users.id'), primary_key=True)
)

members_to_teams_assoc_table = db.Table(
    'members_to_teams', db.metadata,
    db.Column('team', db.ForeignKey('teams.id'), primary_key=True),
    db.Column('member', db.ForeignKey('users.id'), primary_key=True)
)

captains_to_teams_assoc_table = db.Table(
    'captains_to_teams', db.metadata,
    db.Column('team', db.ForeignKey('teams.id'), primary_key=True),
    db.Column('captain', db.ForeignKey('users.id'), primary_key=True)
)

teams_to_games_assoc_table = db.Table(
    'teams_to_games', db.metadata,
    db.Column('team', db.ForeignKey('teams.id'), primary_key=True),
    db.Column('game', db.ForeignKey('games.id'), primary_key=True)
)

players_to_games_assoc_table = db.Table(
    'players_to_games', db.metadata,
    db.Column('player', db.ForeignKey('users.id'), primary_key=True),
    db.Column('game', db.ForeignKey('games.id'), primary_key=True)
)


class Task(db.Model):
    __tablename__ = 'tasks_archive'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    hidden = db.Column(db.Boolean, default=False)
    have_solution = db.Column(db.Boolean, default=False)
    hashed_answer = db.Column(db.String())
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __init__(self, hidden, solution, author):
        self.hidden = hidden
        self.have_solution = solution is not None
        self.author_id = author.id

    def set_ans(self, ans):
        print('new_ans', ans, generate_password_hash(ans))
        if self.hashed_answer is None:
            self.hashed_answer = generate_password_hash(ans)
        else:
            self.hashed_answer += '|' + generate_password_hash(ans)
        print('result', self.hashed_answer)

    def check_ans(self, ans):
        hashed_answers = self.hashed_answer.split('|')
        result = False
        for hashed_answer in hashed_answers:
            if check_password_hash(hashed_answer, ans):
                result = True
        return result

    @property
    def directory(self):
        return os.path.join(Config.TASKS_UPLOAD_FOLDER, f'task_{self.id}')

    @property
    def condition_directory(self):
        return os.path.join(self.directory, "condition")

    @property
    def condition_file_name(self):
        return os.path.join(self.condition_directory, "condition.txt")

    @property
    def condition(self):
        with open(self.condition_file_name, mode="r") as condition_file:
            condition = condition_file.read()
        return condition

    @condition.setter
    def condition(self, condition):
        os.makedirs(self.directory)
        os.makedirs(self.condition_directory)
        with open(self.condition_file_name, mode="w") as condition_file:
            condition_file.write(condition)

    @property
    def solution_directory(self):
        return os.path.join(self.directory, "solution")

    @property
    def solution_file_name(self):
        return os.path.join(self.solution_directory, "solution.txt")

    @property
    def solution(self):
        with open(self.solution_file_name, mode="r") as solution_file:
            solution = solution_file.read()
        return solution

    @solution.setter
    def solution(self, solution):
        os.makedirs(self.solution_directory)
        with open(self.solution_file_name, mode="w") as solution_file:
            solution_file.write(solution)

    def __repr__(self):
        return f"<Task {self.id}>"


class Game(db.Model):
    __tablename__ = 'games'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String)
    game_type = db.Column(db.String)
    start_time = db.Column(db.String)
    end_time = db.Column(db.String)
    game_format = db.Column(db.String)
    privacy = db.Column(db.String)
    info = db.Column(db.Text)
    tasks_positions = db.Column(db.Text)
    tasks_number = db.Column(db.Integer)
    sets_number = db.Column(db.Integer)
    min_team_size = db.Column(db.Integer)
    max_team_size = db.Column(db.Integer)
    solutions = db.Column(db.String)
    authors = orm.relation("User",
                           secondary=authors_to_games_assoc_table,
                           back_populates='authoring')
    teams = orm.relationship('Team',
                             secondary=teams_to_games_assoc_table,
                             back_populates='games')
    players = orm.relation('User',
                           secondary=players_to_games_assoc_table,
                           back_populates='playing')

    def __init__(self, title, game_type, start_time, end_time, game_format,
                 privacy, info, author, task_number, min_team_size,
                 max_team_size, sets_number, tasks_positions):
        self.title = title
        self.game_type = game_type
        self.start_time = start_time
        self.end_time = end_time
        self.game_format = game_format
        self.privacy = privacy
        self.info = info
        self.authors.append(author)
        self.tasks_number = task_number
        self.min_team_size = min_team_size
        self.max_team_size = max_team_size
        self.sets_number = sets_number
        self.tasks_positions = tasks_positions

    @property
    def type(self):
        return self.game_type

    @property
    def is_private(self):
        return self.privacy == "private"

    @property
    def is_team(self):
        return self.game_format == "team"

    @property
    def positions(self):
        positions = self.tasks_positions.split('|')
        positions = list(map(lambda x: x.split(':'), positions))
        return positions

    @positions.setter
    def positions(self, positions):
        positions = list(map(lambda x: ':'.join(x), positions))
        self.tasks_positions = "|".join(positions)

    def get_status(self, time):
        if time < self.start_time_datetime:
            return 'not started'
        elif time > self.end_time_datetime:
            return 'ended'
        else:
            return 'in progress'

    def get_common_info_human_format(self):
        result = [('Название', self.title),
                  ('Тип игры', Consts.DICT_OF_HUMAN_FORMAT[self.game_type]),
                  ('Время начала', self.start_time),
                  ('Время конца', self.end_time),
                  ('Формат игры',
                   Consts.DICT_OF_HUMAN_FORMAT[self.game_format]),
                  ('Приватность игры',
                   Consts.DICT_OF_HUMAN_FORMAT[self.privacy]),
                  ('Описание игры', self.info)]
        return result

    def get_common_info(self):
        result = {'title': self.title,
                  'game_type': self.game_type,
                  'start_time': self.start_time,
                  'end_time': self.end_time,
                  'game_format': self.game_format,
                  'privacy': self.privacy,
                  'info': self.info}
        return result

    def get_tasks_info_human_format(self):
        result = [('Количество задач', self.tasks_number),
                  ('Количество наборов задач', self.sets_number)]
        return result

    def get_tasks_info(self):
        result = {'tasks_number': self.tasks_number,
                  'sets_number': self.sets_number}
        return result

    def get_team_info_human_format(self):
        result = [('Минимальный размер команды', self.min_team_size),
                  ('Максимальный размер команды', self.max_team_size)]
        return result

    def get_team_info(self):
        result = {'max_team_size': self.max_team_size,
                  'min_team_size': self.min_team_size}
        return result

    def get_authors_info_human_format(self):
        result = [('Авторы', ', '.join(self.get_authors_info()))]
        return result

    def get_tasks_positions(self):
        result = list(map(lambda x: x.split(':'),
                          self.tasks_positions.split('|')))
        return result

    def get_authors_info(self):
        result = list(map(lambda author: author.login, self.authors))
        return result

    @property
    def start_time_datetime(self):
        return datetime.strptime(self.start_time, Consts.TIME_FORMAT_FOR_HUMAN)

    @property
    def end_time_datetime(self):
        return datetime.strptime(self.end_time, Consts.TIME_FORMAT_FOR_HUMAN)

    def update_common_info(self, current_title, info, game_type, start_time,
                           end_time, game_format, privacy):
        self.title = current_title
        self.info = info
        self.game_type = game_type
        self.start_time = start_time
        self.end_time = end_time
        self.game_format = game_format
        self.privacy = privacy
        self.tasks_number = Consts.GAMES_DEFAULT_TASK_NUMBERS[game_type]
        self.sets_number = Consts.GAMES_DEFAULT_SETS_NUMBERS[game_type]
        db.session.commit()

    def update_tasks_info(self, title, tasks_number, sets_number):
        self.tasks_number = tasks_number
        self.sets_number = sets_number
        db.session.commit()
        changes = {}
        for i in range(1, self.tasks_number):
            changes[f't{i}'] = dict()
            changes[f't{i}']['number_of_sets'] = sets_number
        update_tasks_info('numbers_of_sets', title, changes)

    def update_team_info(self, min_team_size, max_team_size):
        self.min_team_size = min_team_size
        self.max_team_size = max_team_size
        db.session.commit()

    def update_authors_info(self, authors):
        authors = authors.split(', ')
        self.authors = []
        not_found_users = []
        for author in authors:
            author = db.session.query(User).filter(User.login == author).first()
            if author is None:
                not_found_users.append(author)
            else:
                self.authors.append(author)
                if self not in author.authoring:
                    author.authoring.append(self)
        db.session.commit()
        return not_found_users

    @property
    def tasks_positions_for_render(self):
        tasks_positions = dict()
        for task_position in self.positions:
            if len(task_position) < 2:
                continue
            position, task_id = task_position
            task_id = int(task_id)
            task = db.session.query(Task).filter(Task.id == task_id).first()
            tasks_positions[position] = task
        tasks_positions = dict(tasks_positions)
        return tasks_positions


def create_tasks_tables(game_id, tasks_number):
    db_path = Config.TASKS_STATES_DB
    engine = sql.create_engine('sqlite:///' + db_path)
    metadata = sql.MetaData(engine)
    game = db.session.query(Game).filter(Game.id == game_id).first()
    state_table = sql.Table(f"{game_id}_states", metadata,
                            sql.Column('id', sql.Integer, primary_key=True),
                            sql.Column('login', sql.String),
                            sql.Column('picked_tasks', sql.String),
                            *[sql.Column('t' + str(i), sql.Integer)
                              for i in range(1, tasks_number + 1)])
    if game.game_type == 'domino':
        numbers_of_sets_table = sql.Table(f"{game_id}_numbers_of_sets",
                                          metadata,
                                          sql.Column('id',
                                                     sql.Integer,
                                                     primary_key=True),
                                          sql.Column(
                                              'current_checking_id',
                                              sql.Integer),
                                          sql.Column('key',
                                                     sql.String),
                                          sql.Column('number_of_sets',
                                                     sql.Integer)
                                          )
        dict_of_attrs = {'number_of_sets': game.sets_number}
    else:
        numbers_of_sets_table = sql.Table(f"{game_id}_numbers_of_sets",
                                          metadata,
                                          sql.Column('id',
                                                     sql.Integer,
                                                     primary_key=True),
                                          sql.Column(
                                              'current_checking_id',
                                              sql.Integer),
                                          sql.Column('key',
                                                     sql.String),
                                          sql.Column('cost',
                                                     sql.Integer),
                                          sql.Column('number_of_sets',
                                                     sql.Integer)
                                          )
        dict_of_attrs = dict([('number_of_sets', game.sets_number),
                              ('cost', 16)])

    class Tasks(object):
        def __init__(self, kwargs):
            for item in kwargs.items():
                setattr(self, item[0], item[1])

    metadata.create_all(engine)
    orm.mapper(Tasks, numbers_of_sets_table)
    _session = orm.sessionmaker(bind=engine)
    session = _session()
    dict_of_attrs['current_checking_id'] = 1
    for i in range(1, game.tasks_number + 1):
        new_dict_of_attrs = dict_of_attrs.copy()
        new_dict_of_attrs['key'] = f't{i}'
        task = Tasks(new_dict_of_attrs)
        session.add(task)
    session.commit()


def add_user_to_game_table(login, game_id):
    session, UserTasks = get_session_for_game_table(game_id, "states")
    game = db.session.query(Game).filter(Game.id == game_id).first()
    dict_of_attr = {'login': login}
    if game.game_type == 'domino':
        dict_of_attr['picked_tasks'] = ''
    for i in range(1, game.tasks_number + 1):
        dict_of_attr[f't{i}'] = '0ok'
    user = UserTasks(dict_of_attr)
    session.add(user)
    session.commit()


def get_results(game_id):
    session, UserTasks = get_session_for_game_table(game_id, "states")
    game = db.session.query(Game).filter(Game.id == game_id).first()
    result = []
    users_states = session.query(UserTasks).filter(True).all()
    for user_states in users_states:
        new_result = []
        s = 0
        login = user_states.login
        if not game.is_private:
            title = login
        else:
            team = db.session.query(Team).filter(Team.login == login).first()
            title = team.title
        new_result.append(title)
        for i in range(1, game.tasks_number + 1):
            new_result.append(getattr(user_states, f't{i}'))
            print(user_states)
            s += int(new_result[-1][:-2])
        new_result.append(s)
        result.append(new_result)
    result.sort(key=lambda x: -x[-1])
    return result


def get_tasks_info(table_title, game_id, login=None):
    session, UserTasks = get_session_for_game_table(game_id, table_title)
    game = db.session.query(Game).filter(Game.id == game_id).first()
    result = dict()
    if login is not None:
        user_states = session.query(UserTasks).filter(UserTasks.login
                                                      == login).first()
        if game.game_type == 'domino':
            result['picked_tasks'] = getattr(user_states,
                                             'picked_tasks').split()
        else:
            result['picked_tasks'] = Consts.TASKS_KEYS['penalty']
        for i in range(1, game.tasks_number + 1):
            result[f't{i}'] = getattr(user_states, f't{i}')
    else:
        tasks = session.query(UserTasks).filter(True).all()
        for task in tasks:
            result[task.key] = {'number_of_sets': task.number_of_sets}
            result[task.key]['current_checking_id'] = task.current_checking_id
            if game.game_type == 'penalty':
                result[task.key]['cost'] = task.cost
    return result


def get_session_for_game_table(game_id, table_title):
    class UserTasks(object):
        def __init__(self, kwargs):
            for item in kwargs.items():
                setattr(self, item[0], item[1])

    db_path = Config.TASKS_STATES_DB
    engine = sql.create_engine('sqlite:///' + db_path)
    metadata = sql.MetaData(engine)
    table = sql.Table(f"{game_id}_{table_title}", metadata, autoload=True)
    orm.mapper(UserTasks, table)
    session = orm.sessionmaker(bind=engine)()
    return session, UserTasks


def update_tasks_info(table_title, game_id, changes, login=None):
    session, UserTasks = get_session_for_game_table(game_id, table_title)
    if login is not None:
        user_states = session.query(UserTasks).filter(UserTasks.login
                                                      == login).first()
        for state in changes.items():
            setattr(user_states, state[0], state[1])
        session.commit()
    else:

        for change in changes.items():
            task = session.query(UserTasks).filter(UserTasks.key ==
                                                   change[0]).first()
            for attr in change[1].items():
                setattr(task, attr[0], attr[1])
            session.commit()


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer,
                   primary_key=True, autoincrement=True, index=True)
    name = db.Column(db.String, nullable=False)
    surname = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    info = db.Column(db.Text, nullable=True)
    email = db.Column(db.String, nullable=False)
    hashed_email = db.Column(db.String, nullable=False)
    login = db.Column(db.String, nullable=False)
    hashed_password = db.Column(db.String, nullable=False)
    created_tasks = orm.relationship("Task")
    rights = db.Column(db.String, nullable=False, default='user')
    authoring = orm.relationship('Game',
                                 secondary=authors_to_games_assoc_table,
                                 back_populates="authors")
    playing = orm.relationship('Game',
                               secondary=players_to_games_assoc_table,
                               back_populates='players')
    captaining = orm.relationship('Team',
                                  secondary=captains_to_teams_assoc_table,
                                  back_populates='captain')
    teams = orm.relationship('Team',
                             secondary=members_to_teams_assoc_table,
                             back_populates='members')
    is_authenticated = True

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def set_email(self, email):
        self.email = email
        self.hashed_email = generate_password_hash(email)

    def __init__(self, params):
        self.login = params['login']
        self.name = params['name']
        self.surname = params['surname']
        self.last_name = params['last_name']
        self.info = params['info']
        self.rights = params['rights']

    def available_for_game(self, game: Game) -> bool:
        return self not in game.players

    def can_register_for_game(self, game: Game) -> bool:
        result = False
        if game.is_team:
            for team in self.captaining:
                if team.available_for_game(game):
                    result = True
        else:
            result = self.available_for_game(game)
        return result

    def register_for_game(self, game: Game):
        game.players.append(self)
        db.session.commit()
        add_user_to_game_table(self.login, game.id)

    def get_general_info(self):
        return {"login": self.login,
                "name": self.name,
                "surname": self.surname,
                "last_name": self.last_name,
                "rights": self.rights_list}

    @property
    def rights_list(self):
        return self.rights.split()

    def get_teams_info(self):
        teams_info = []
        for team in self.teams:
            teams_info.append(team.get_info())
        return teams_info

    def get_team_for_game(self, game):
        res = None
        if game.game_format == 'personal':
            res = self
        else:
            for team in self.teams:
                if game in team.games:
                    res = team
        return res

    def is_captain_of_team(self, team):
        return team in self.captaining


class Team(db.Model):
    __tablename__ = 'teams'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer,
                   primary_key=True, autoincrement=True, index=True)
    title = db.Column(db.String, nullable=False)
    login = db.Column(db.String, nullable=False)
    hashed_password = db.Column(db.String, nullable=False)
    members = orm.relation('User',
                           secondary=members_to_teams_assoc_table,
                           back_populates='teams')
    captain = orm.relation('User',
                           secondary=captains_to_teams_assoc_table,
                           back_populates='captaining')
    games = orm.relation('Game',
                         secondary=teams_to_games_assoc_table,
                         back_populates='teams')

    def __init__(self, title, login):
        self.title = title
        self.login = login

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def available_for_game(self, game: Game):
        result = True
        if not game.min_team_size <= len(self.members) <= game.max_team_size:
            result = False
        for member in self.members:
            if member in game.players:
                result = False
        return result

    def register_for_game(self, game: Game):
        game.teams.append(self)
        for member in self.members:
            if member not in game.players:
                game.players.append(member)
        db.session.commit()
        add_user_to_game_table(self.login, game.id)

    def get_info(self):
        info = dict()
        info['title'] = self.title
        info['captain'] = f"{self.captain[0].name}" \
                          f" {self.captain[0].surname}" \
                          f" {self.captain[0].last_name}"
        info['members'] = []
        for player in self.members:
            info['members'].append(player.get_general_info())
        info['size'] = len(info['members'])
        return info


def get_game(title):
    game = db.session.query(Game).filter(Game.title == title)
    if game.first() is not None:
        return game.first()
    return 'Not found'


def create_game(title, game_type, start_time, end_time, game_format, privacy,
                info, author, min_team_size=4, max_team_size=4):
    task_number = Consts.GAMES_DEFAULT_TASK_NUMBERS[game_type]
    sets_number = Consts.GAMES_DEFAULT_SETS_NUMBERS[game_type]
    tasks_positions = Consts.GAMES_DEFAULT_TASKS_POSITIONS[game_type]
    game = Game(title, game_type, start_time, end_time, game_format, privacy,
                info, author, task_number, min_team_size, max_team_size,
                sets_number, tasks_positions)
    author.authoring.append(game)
    db.session.add(game)
    db.session.commit()
    create_tasks_tables(game.id, task_number)


def get_team_by_id(team_id):
    team = db.session.query(Team).filter(Team.id == team_id).first()
    if team is None:
        return "Not found"
    return team
