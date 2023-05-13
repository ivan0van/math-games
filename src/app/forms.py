from flask_wtf import FlaskForm
from flask_wtf.file import *
from wtforms import *
from wtforms.validators import *

from src.Globals import Constants


def is_task_validator(form_for_validation, field):
    game_type = form_for_validation.game_type.data
    task = field.data
    if game_type == "domino":
        if task not in Constants.VALID_DOMINO_TASKS_NUMBERS:
            raise ValidationError("Номер задачи не прошёл проверку")
    elif game_type == "penalty":
        if task not in Constants.VALID_PENALTY_TASKS_NUMBERS:
            raise ValidationError("Номер задачи не прошёл проверку")


IS_NAME_VALIDATOR = Regexp(regex="^[А-Я+Ё][а-я+ё]+",
                           message="Неверный формат записи")
DATA_REQUIRED_VALIDATOR = InputRequired(
                           message="Это поле обязательно для заполнения")
DATETIME_VALIDATOR = Regexp(regex=Constants.DATE_REGEXP,
                            message="Некорректная дата")
IS_TASK_VALIDATOR = is_task_validator
ALL_IMAGES_FILES = FileAllowed(Constants.ALLOWED_IMAGE_EXTENSIONS,
                               message="Неправильный формат файла")
ALL_TEXT_FILES = FileAllowed(Constants.ALLOWED_TEXT_EXTENSIONS,
                             message="Неправильный формат файла")
EMAIL_VALIDATOR = Email(message="Формат ввода Email неправильный")

GAME_TYPE_CHOICES = [("domino", "Домино"), ("penalty", "Пенальти")]
RIGHT_CHOICES = [('author', 'Автор')]


class LoginForm(FlaskForm):
    login = StringField("Логин", validators=[DATA_REQUIRED_VALIDATOR])
    password = PasswordField("Пароль", validators=[DATA_REQUIRED_VALIDATOR])
    submit = SubmitField("Вход")


class SignUpStudentForm(FlaskForm):
    login = StringField("Логин*", validators=[DATA_REQUIRED_VALIDATOR])
    password = PasswordField("Пароль*", validators=[DATA_REQUIRED_VALIDATOR])

    email = StringField("Email*", validators=[DATA_REQUIRED_VALIDATOR,
                                              EMAIL_VALIDATOR])
    name = StringField("Имя*", validators=[DATA_REQUIRED_VALIDATOR,
                                           IS_NAME_VALIDATOR])
    surname = StringField("Фамилия*", validators=[DATA_REQUIRED_VALIDATOR,
                                                  IS_NAME_VALIDATOR])
    last_name = StringField("Отчество*", validators=[DATA_REQUIRED_VALIDATOR,
                                                     IS_NAME_VALIDATOR])
    info = StringField("Дополнительная информация о Вас"
                       "(как с Вами можно связаться, "
                       "что Вы хотите рассказать о себе)")
    submit = SubmitField("Зарегистрироваться")


class ForgotPassword(FlaskForm):
    email = StringField("Email", validators=[DATA_REQUIRED_VALIDATOR,
                                             EMAIL_VALIDATOR])
    submit = SubmitField("Восстановить пароль")


class AddTaskForm(FlaskForm):
    condition = TextAreaField("Условие задачи (Синтаксис MathJax)",
                              validators=[DATA_REQUIRED_VALIDATOR])
    solution = TextAreaField("Решение задачи (Синтаксис MathJax)", )
    answer = StringField("Ответ", validators=[DATA_REQUIRED_VALIDATOR])
    hidden = BooleanField("Задача скрыта")
    submit = SubmitField("Добавить задачу")


class RegisterTeamToGameForm(FlaskForm):
    team_id = SelectField('Выберите команду', coerce=int)
    submit = SubmitField("Зарегистрировать команду")


class RegisterPlayerToGameForm(FlaskForm):
    submit = SubmitField("Зарегистрироваться")


class GameCommonInfoForm(FlaskForm):
    title = StringField('Название игры', validators=[DATA_REQUIRED_VALIDATOR])
    info = TextAreaField('Описание игры', validators=[DATA_REQUIRED_VALIDATOR])
    game_type = SelectField('Тип игры', choices=Constants.GAMES_DICT,
                            coerce=str)
    start_time = StringField('Время начала в формате дд.мм.гггг чч:мм:сс',
                             validators=[DATETIME_VALIDATOR])
    end_time = StringField('Время конца в формате дд.мм.гггг чч:мм:сс',
                           validators=[DATETIME_VALIDATOR])
    game_format = SelectField('Формат игры', choices=[('personal', 'личная'),
                                                      ('team', 'командная')])
    privacy = SelectField('Приватность игры', choices=[('private', 'закрытая'),
                                                       ('open', 'открытая')])
    submit = SubmitField("Создать/изменить игру")

    def set_defaults(self, defaults):
        self.title.data = defaults['title']
        self.info.data = defaults['info']
        self.game_type.data = defaults['game_type']
        self.start_time.data = defaults['start_time']
        self.end_time.data = defaults['end_time']
        self.game_format.data = defaults['game_format']
        self.privacy.data = defaults['privacy']


class GameTasksInfoForm(FlaskForm):
    tasks_number = IntegerField('Количество задач',
                                validators=[DATA_REQUIRED_VALIDATOR])
    sets_number = IntegerField('Количество наборов задач',
                               validators=[DATA_REQUIRED_VALIDATOR])
    submit = SubmitField('Подтвердить изменения')

    def set_defaults(self, defaults):
        self.tasks_number.data = defaults['tasks_number']
        self.sets_number.data = defaults['sets_number']


class GameTeamInfoForm(FlaskForm):
    min_team_size = IntegerField('Минимальный размер команды',
                                 validators=[DATA_REQUIRED_VALIDATOR])
    max_team_size = IntegerField('Максимальный размер команды',
                                 validators=[DATA_REQUIRED_VALIDATOR])
    submit = SubmitField('Подтвердить изменения')

    # Установить дефолтные значения
    def set_defaults(self, defaults):
        self.min_team_size.data = defaults['min_team_size']
        self.max_team_size.data = defaults['max_team_size']


class GameAuthorsInfoForm(FlaskForm):
    authors = StringField('Логины авторов через запятую с пробелом')
    submit = SubmitField('Подтвердить изменения')

    def set_defaults(self, defaults):
        self.authors.data = defaults['authors']


class EnterTeamForm(FlaskForm):
    login = StringField("Логин", validators=[DATA_REQUIRED_VALIDATOR])
    password = PasswordField("Пароль", validators=[DATA_REQUIRED_VALIDATOR])
    submit1 = SubmitField("Вступить")


class CreateTeamForm(FlaskForm):
    title = StringField('Название команды',
                        validators=[DATA_REQUIRED_VALIDATOR])
    login = StringField('Логин', validators=[DATA_REQUIRED_VALIDATOR])
    password = PasswordField('Пароль', validators=[DATA_REQUIRED_VALIDATOR])
    submit2 = SubmitField('Создать')


''' ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ '''


def get_extension(filename):
    if '.' not in filename:
        return ""

    return filename.rsplit('.', 1)[1].lower()
