# -*- coding: utf-8 -*-
from flask import render_template, request, redirect
from flask_login import logout_user, current_user, login_user

from src.app import app
from src.app import login_manager
from src.app.forms import *
from src.app.models import *

from src.app.game_engine import create_engine

DICT_OF_FORMS = {'tasks': GameTasksInfoForm,
                 'common': GameCommonInfoForm,
                 'team': GameTeamInfoForm,
                 'authors': GameAuthorsInfoForm}


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    params = dict()
    params['title'] = 'Мат игры'
    return render_template('index.html', **params)


@app.route('/sign_up/', methods=['GET', 'POST'])
def sign_up():
    sign_up_form = SignUpStudentForm()
    params = dict()
    params["title"] = "Регистрация"
    params["form"] = sign_up_form
    if sign_up_form.validate_on_submit():
        if is_auth():
            logout_user()
        login = request.form.get('login')
        login_used_query = db.session.query(User).filter(User.login ==
                                                         login)
        login_used = login_used_query.scalar() is not None
        if login_used:
            params["login_used"] = True
            return render_template("sign_up_user.html", **params)
        user = User({'login': request.form.get("login"),
                     'name': request.form.get("name"),
                     'surname': request.form.get("surname"),
                     'last_name': request.form.get('last_name'),
                     'info': request.form.get("info"),
                     'rights': "captain author user"})
        user.set_password(request.form.get("password"))
        user.set_email(request.form.get("email"))
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)
        return redirect("/")
    return render_template("sign_up_user.html", **params)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    params = dict()
    params["title"] = "Вход"
    params["form"] = form
    if form.validate_on_submit():
        session = db.session
        user = session.query(User).filter(User.login == form.login.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=True)
            return redirect("/profile/common")
        return render_template('login.html', invalid_parameters=True, form=form)
    return render_template("login.html", **params)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect('/login')


def register_to_team(team_login, password):
    team = db.session.query(Team).filter(Team.login == team_login).first()
    render_params = dict()
    render_params["login"] = team_login
    render_params["last"] = "/profile/user"
    if team is None:
        return render_template('team_not_found.html', **render_params)
    if not team.check_password(password):
        return render_template('wrong_password.html', **render_params)
    team.members.append(current_user)
    db.session.commit()
    return render_template('success.html', **render_params)


def create_team(title, login, password):
    if db.session.query(Team).filter(Team.title == title).first() is not None:
        return render_template('team_already_exists.html',
                               attribute='названием', value=title, last='/')
    if db.session.query(Team).filter(Team.login == login).first() is not None:
        return render_template('team_already_exists.html',
                               attribute='логином', value=login, last='/')
    team = Team(title, login)
    team.set_password(password)
    current_user.captaining.append(team)
    current_user.teams.append(team)
    db.session.add(team)
    db.session.commit()
    return render_template('success.html',
                           last='../profile/user')


@app.route("/profile/common", methods=["GET"])
def profile_common():
    if not is_auth():
        return redirect("/login")
    render_params = {"dict_of_rights": Consts.DICT_OF_RIGHTS}
    render_params.update(current_user.get_general_info())
    return render_template("profile.html", **render_params)


@app.route("/profile/user", methods=["GET", "POST"])
def profile_user():
    if not is_auth():
        return redirect("/login")
    if "user" not in current_user.rights_list:
        return render_template("what_are_you_doing_here.html")
    enter_form = EnterTeamForm()
    create_form = CreateTeamForm()
    if enter_form.submit1.data and enter_form.validate():
        return register_to_team(request.form.get("login"),
                                request.form.get("password"))
    if create_form.submit2.data and create_form.validate():
        return create_team(request.form.get("title"), request.form.get("login"),
                           request.form.get("password"))
    render_params = {"enter_form": enter_form, "create_form": create_form,
                     "teams": current_user.get_teams_info(),
                     "rights": current_user.rights_list,
                     "dict_of_rights": Consts.DICT_OF_RIGHTS}
    render_params.update(current_user.get_general_info())
    return render_template("profile_teams.html", **render_params)


@app.route("/profile/author", methods=["GET", "POST"])
def profile_author():
    if not is_auth():
        return redirect("/login")
    if "author" not in current_user.rights_list:
        return render_template("what_are_you_doing_here.html")
    games = []
    for game in current_user.authoring:
        new_game = {'common': game.get_common_info_human_format(),
                    'tasks': game.get_tasks_info_human_format(),
                    'tasks_positions': game.get_tasks_positions(),
                    'authors': game.get_authors_info_human_format()}
        if game.is_team:
            new_game['team'] = game.get_team_info_human_format()
        else:
            new_game['team'] = [('Минимальный размер команды', '-'),
                                ('Максимальный размер команды', '-')]
        games.append(new_game)
    render_params = {"games": games, "dict_of_rights": Consts.DICT_OF_RIGHTS}
    render_params.update(current_user.get_general_info())
    return render_template('profile_author.html', **render_params)


@app.route("/games_info/common", methods=["GET"])
def article_common():
    games = db.session.query(Game).filter(True).all()
    formatted_games = []
    for game in games:
        register = current_user in game.players
        new_formatted_game = {'game_type_human_format':
                              Consts.DICT_OF_HUMAN_FORMAT[game.game_type],
                              'game_format_human_format':
                              Consts.DICT_OF_HUMAN_FORMAT[game.game_format],
                              'register': register}
        new_formatted_game.update(game.get_common_info())
        if (register or current_user.can_register_for_game(game)) \
                and game.end_time_datetime > datetime.today() \
                and not game.is_private:
            formatted_games.append(new_formatted_game)
    render_params = {"games": formatted_games}
    return render_template('games_info.html', **render_params)


@app.route('/registration_to_game/<game_title>', methods=['POST', 'GET'])
def registration_to_game(game_title):
    if not is_auth():
        return redirect("/login")
    game = get_game(game_title)
    if game == "Not found" or game.is_private:
        return render_template("what_are_you_doing_here.html")
    unit = current_user
    if game.is_team:
        available_teams = []
        for team in current_user.teams:
            if team.available_for_game(game):
                available_teams.append((team.id, team.title))
        is_available = len(available_teams) != 0
        choose_form = RegisterTeamToGameForm()
        choose_form.team_id.choices = available_teams
    else:
        is_available = current_user.available_for_game(game)
        choose_form = RegisterPlayerToGameForm()
    if not is_available:
        return render_template("what_are_you_doing_here.html")
    if choose_form.validate_on_submit():
        if game.is_team:
            unit = get_team_by_id(choose_form.team_id.data)
        unit.register_for_game(game)
        return render_template("success.html", last="/games_info/common")
    render_params = {"title": "Регистрация на игру",
                     "is_team": game.is_team, "form": choose_form}
    return render_template("form_with_title.html", **render_params)


@app.route('/create_game_form/', methods=['POST', 'GET'])
def create_game_form():
    if not is_auth():
        return redirect("/login")
    if "author" not in current_user.rights_list:
        return render_template("what_are_you_doing_here.html")
    form = GameCommonInfoForm()
    render_params = {"form": form, "title": "Создание игры"}
    if form.validate_on_submit():
        if get_game(request.form.get('title')) != "Not found":
            render_params["error"] = "Игра с таким названием уже существует"
        else:
            create_game(request.form.get('title'),
                        request.form.get('game_type'),
                        request.form.get('start_time'),
                        request.form.get('end_time'),
                        request.form.get('game_format'),
                        request.form.get('privacy'),
                        request.form.get('info'), current_user)
            return render_template('success.html', last='/profile/author')
    return render_template('form_with_title.html', **render_params)


@app.route('/update_game/<game_title>/<block>', methods=["POST", "GET"])
def update_game(game_title, block):
    if not is_auth():
        return redirect("/login")
    if 'author' not in current_user.rights_list:
        return render_template("what_are_you_doing_here.html")
    game = get_game(game_title)
    if game == "Not found" or game not in current_user.authoring:
        return render_template("what_are_you_doing_here.html")
    form = DICT_OF_FORMS[block].__call__()
    if block == 'common':
        default = game.get_common_info()
    elif block == 'tasks':
        default = game.get_tasks_info()
    elif block == 'team':
        default = game.get_team_info()
    elif block == 'authors':
        default = {'authors': ', '.join(game.get_authors_info())}
    else:
        return render_template('what_are_you_doing_here.html')
    if form.validate_on_submit():
        data = list(request.form.values())[1:-1]
        if block == 'common':
            game.update_common_info(*data)
        elif block == 'tasks':
            game.update_tasks_info(*data)
        elif block == 'team':
            game.update_team_info(*data)
        elif block == 'authors':
            not_found_users = game.update_authors_info(*data)
            if len(not_found_users) != 0:
                return render_template('users_not_found.html',
                                       users=not_found_users,
                                       last='../../profile/author')
        return render_template('success.html', last='../../profile/author')
    form.set_defaults(default)
    return render_template('form_with_title.html', form=form, default=default)


def create_task(hidden, condition, solution, answer, position, value, author,
                game):
    if not is_auth():
        return redirect("/login")
    task = Task(hidden, solution, author)
    for ans in answer.split('|'):
        task.set_ans(ans)
    db.session.add(task)
    db.session.flush()
    db.session.refresh(task)
    task.condition = condition
    task.solution = solution
    db.session.add(task)
    positions = game.positions
    positions[positions.index([position, value])] = (position, str(task.id))
    game.positions = positions
    db.session.commit()


@app.route('/add_task/<game_title>/<task_position>/<current_value>',
           methods=['GET', 'POST'])
def add_task(game_title, task_position, current_value):
    if not is_auth():
        return redirect("/login")
    if 'author' not in current_user.rights_list:
        return render_template("what_are_you_doing_here.html")
    add_task_form = AddTaskForm()
    render_params = dict()
    render_params['title'] = 'Добавить Задачу'
    render_params['add_task_form'] = add_task_form
    render_params['success'] = False
    if add_task_form.validate_on_submit():
        game = get_game(game_title)
        if game == "Not found":
            return render_template('what_are_you_doing_here.html')
        if task_position not in Consts.TASKS_POSITIONS[game.type]:
            return render_template('what_are_you_doing_here.html')
        create_task(request.form.get("hidden") == 'y',
                    request.form.get("condition"),
                    request.form.get("solution"),
                    request.form.get("answer"),
                    task_position, current_value,
                    current_user, game)
        return render_template("success.html", last='/profile/author')
    return render_template('add_task.html', **render_params)


@app.route('/archive/')
@app.route('/tasks/')
def archive():
    render_params = dict()
    render_params['title'] = 'Архив'
    tasks_table = db.session.query(Task).filter(Task.hidden is False)
    render_params["tasks_table"] = tasks_table
    return render_template("archive.html", **render_params)


@app.route('/tasks/<int:task_id>')
def task(task_id):
    params = dict()
    params['title'] = 'Задача ' + str(task_id)
    task = db.session.query(Task).filter(Task.id == task_id).first()
    if not task:
        return render_template("no_task.html")
    if task.hidden:
        if not is_auth():
            return render_template("what_are_you_doing_here.html")
        if not current_user.id == task.author_id:
            return render_template("what_are_you_doing_here.html")
    params['task'] = task
    params["condition"] = task.condition
    if task.have_solution:
        params["have_solution"] = True
        params["solution"] = task.solution
    return render_template("task.html", **params)


def get_js_format_time(time):
    return datetime.strftime(time, Consts.TIME_FORMAT_FOR_JS)


@app.route("/game/<game_title>", methods=["GET", "POST"])
def game(game_title):
    if not is_auth():
        return redirect("/login")
    game = get_game(game_title)
    if game is None:
        return render_template('what_are_you_doing_here.html')
    current_team = current_user.get_team_for_game(game)
    if current_team is None:
        return render_template('error.html',
                               message='Ваша команда не зарегистрирована  на '
                                       'игру', last='../../')
    if game.game_format == 'personal':
        is_captain = True
    else:
        is_captain = current_user.is_captain_of_team(current_team)
    time = datetime.now()
    status = game.get_status(time)
    html_page = Consts.DICT_OF_GAME_PAGES[game.type]
    render_params = {"title": game_title, "status": status,
                     "start_time": get_js_format_time(game.start_time_datetime),
                     "end_time": get_js_format_time(game.end_time_datetime),
                     "now_time": get_js_format_time(time)}
    game_engine = create_engine(game, current_team)
    if status == 'not_started':
        return render_template(html_page, **render_params)
    if status == 'ended':
        return render_template("game_ended.html", **render_params)
    if request.method == "POST":
        if request.form.get("picked") and is_captain:
            game_engine.pick_task(request.form.get("picked"))
        elif request.form.get('answer') and is_captain:
            game_engine.handle_answer(request.form.get("name"),
                                      request.form.get("answer"))
        else:
            return render_template('error.html', last=f'/game/{game_title}',
                                   message='У вас нет прав на сдачу задач')
    other_params = {"keys": Consts.TASKS_KEYS[game.type],
                    "state": status,
                    "is_member": not is_captain,
                    "title": game.title}
    render_params.update(other_params)
    render_params.update(game_engine.get_info())
    return render_template(html_page, **render_params)


def get_point(state):
    return int(state[:-2])


@app.route('/results/<game_title>')
def results(game_title):
    game = get_game(game_title)
    if game is None:
        return render_template('what_are_you_doing_here.html')
    current_team = None
    if is_auth():
        if game.game_format == 'personal':
            if game in current_user.playing:
                current_team = current_user
        else:
            for team in current_user.captaining:
                if game in team.games:
                    current_team = team
            if current_team is None:
                for team in current_user.teams:
                    if game in team.games:
                        current_team = team
    team = ''
    if is_auth() and current_team is not None:
        team = current_team
    results = get_results(game.id)
    numbers_of_solved = []
    step = 1
    for result in results:
        x = 0
        for state in result[step:-1]:
            if get_point(state) > 0:
                x += 1
        numbers_of_solved.append(x)
    render_params = {"team": team, "results": results, "team_num": len(results),
                     "numbers_of_solved": numbers_of_solved,
                     "title": Consts.TITLES_DICT[game.type],
                     "keys": Consts.TASKS_KEYS[game.type],
                     "number": Consts.GAMES_DEFAULT_TASK_NUMBERS[game.type],
                     "info": Consts.TASKS_POSITIONS_BY_KEYS[game.type],
                     "to_game": f"/game/{game_title}"}
    return render_template("results.html", **render_params)


''' ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ '''


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).filter(User.id == user_id).first()


def is_auth():
    return current_user.is_authenticated
