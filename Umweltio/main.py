from flask import Flask, render_template, redirect, request, url_for, session, flash, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Boolean, DateTime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import timedelta
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import jwt

app = Flask(__name__)
app.secret_key = "DIMONTURURURU"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diary.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


UPLOAD_FOLDER = 'static/profile_pics'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    is_confirmed = db.Column(db.Boolean, default=False)
    content = db.Column(db.String(500), nullable=True)  
    status = db.Column(db.String(20), default="Участник")
    registration_date = db.Column(db.DateTime, default=datetime.utcnow) 
    profile_picture = db.Column(db.String(200), default='profile_pics/default_profile.png', nullable=True)
    points = db.Column(db.Integer, default=0)
    correct_answers = db.Column(db.Integer, default=0)
    quizzes_completed = db.Column(db.Integer, default=0)

   

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='messages')

@app.before_request
def create_tables():
    db.create_all()

def generate_confirmation_token(user_id):
    exp = datetime.utcnow() + timedelta(days=7)
    token = jwt.encode({'user_id': user_id, 'exp': exp}, 'DIMONTURURURU', algorithm='HS256')
    return token


def generate_confirmation_link(user_id):
    token = generate_confirmation_token(user_id) 
    confirmation_link = url_for('confirm_email', token=token, _external=True)
    return confirmation_link

def send_confirmation_email(email, confirmation_link):
    sender_email = "umweltio2009@gmail.com"
    sender_password = "xxvl vxus ycqw sqbp"

    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = "Подтверждение регистрации "

    body = f"Спасибо за регистрацию! Пожалуйста, подтвердите ваш адрес электронной почты, перейдя по следующей ссылке: {confirmation_link}"
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print("Письмо отправлено!")
    except Exception as e:
        print(f"Ошибка при отправке письма: {e}")

    return redirect(url_for('home'))

def delete_unconfirmed_users():
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    unconfirmed_users = User.query.filter(User.is_confirmed == False, User.registration_date < seven_days_ago).all()
    
    for user in unconfirmed_users:
        db.session.delete(user)
    
    db.session.commit()
    print(f"Удалено {len(unconfirmed_users)} неподтвержденных пользователей.")

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=7)

@app.before_request
def load_user():
    g.user = get_current_user()  

@app.before_request
def check_unconfirmed_users():
    delete_unconfirmed_users()



@app.route('/', methods=['GET', 'POST'])
def home():
    user = get_current_user()

    return render_template('index.html', user=g.user)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if g.user is None:
        print('Salamaleikum')
        

    user = g.user
    print(f"Статус is_confirmed в профиле: {user.is_confirmed}")
    
    if request.method == 'POST':
        if 'file' not in request.files or request.files['file'].filename == '':
            return render_template('profile.html', user=user, message='Файл не выбран')

        file = request.files['file']
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        user.profile_picture = f'profile_pics/{filename}'
        db.session.commit()
        return render_template('profile.html', user=user,message='Фото профиля было изменёно')
    
    return render_template('profile.html', user=user)
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        if User.query.filter_by(username=username).first():
            return render_template('register.html', message='Такой пользователь уже существует!')
        if User.query.filter_by(email=email).first():
            return render_template('register.html', message='Эта почта уже используется!')

        new_user = User(username=username,
                        password=generate_password_hash(password, method='pbkdf2:sha256'),
                        email=email, content='', status='Участник')  
        db.session.add(new_user)
        db.session.commit()

       
        token = generate_confirmation_token(new_user.id) 
        confirmation_link = url_for('confirm_email', token=token, _external=True)
        
      
        send_confirmation_email(email, confirmation_link)

        flash('Пожалуйста, проверьте вашу почту для подтверждения аккаунта.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/confirm_email/<token>', methods=['GET'])
def confirm_email(token):
    try:
        data = jwt.decode(token, 'DIMONTURURURU', algorithms=['HS256'])
        user_id = data.get('user_id')

        user = User.query.get(user_id)
        if user:
            if not user.is_confirmed:
                user.is_confirmed = True
                db.session.commit()
                flash('Ваш адрес электронной почты был подтвержден!')
            else:
                flash('Ваш адрес электронной почты уже подтвержден!')
            return redirect(url_for('confirmed_email'))
        else:
            flash('Пользователь не найден.')
            return redirect(url_for('home'))

    except jwt.ExpiredSignatureError:
        flash('Срок действия ссылки истек.')
        return redirect(url_for('home'))
    except jwt.InvalidTokenError:
        flash('Неверная ссылка.')
        return redirect(url_for('home'))

@app.route('/confirmed_email')
def confirmed_email():
    return render_template('email_confirmed.html', user=g.user)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['username'] = user.username
            session['email'] = user.email  
            session['user_id'] = user.id 
            return redirect(url_for('home'))  
        else:
            return render_template('login.html', user=g.user, message='Неправильное имя или пароль')

    return render_template('login.html', user=g.user)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        session.pop('username', None)
        session.pop('user_id', None) 
        flash('Вы вышли из аккаунта ', 'info')  
        return redirect(url_for('home'))

    return render_template('confirm_logout.html', user=g.user)  

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    user = g.user 
    if request.method == 'POST':  
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            return render_template('change_password.html', user=user)  
        
        user_from_db = User.query.filter_by(username=session['username']).first()
        if user_from_db and check_password_hash(user_from_db.password, current_password):
            if new_password == confirm_password:
                user_from_db.password = generate_password_hash(new_password)
                db.session.commit()
                flash('Пароль был изменён.')
                return redirect(url_for('profile'))
            else:
                return render_template('change_password.html', user=user, message='Пароли не соответствуют.')  
        else:
            return render_template('change_password.html', user=user, message='Неправильный пароль.')  

    return render_template('change_password.html', user=user)  

@app.route('/change_email', methods=['GET', 'POST'])
def change_email():
    message = None 
    if request.method == 'POST':
        current_email = request.form.get('current_email')
        new_email = request.form.get('new_email')

        if current_email and new_email:
            user = User.query.filter_by(email=current_email).first()

            if user:
                existing_user = User.query.filter_by(email=new_email).first()
                if existing_user:
                    message = 'Эта почта уже используется другим пользователем.'
                    return render_template('change_email.html', user=user, message=message)

                user.email = new_email
                user.is_confirmed = False  
                db.session.commit()

        
                session['email'] = new_email

                
                confirmation_link = generate_confirmation_link(user.id)
                send_confirmation_email(new_email, confirmation_link)

                flash('Почта была изменена. Пожалуйста, подтвердите новый адрес электронной почты.')
                return redirect(url_for('profile'))
            else:
                message = 'Почта не найдена.'  
                return render_template('change_email.html', user=user, message=message)

    return render_template('change_email.html', user=g.user, message=message)


@app.route('/change_username', methods=['GET', 'POST'])
def change_username():
    user = g.user 
    if request.method == 'POST':
        current_username = request.form.get('current_username')  
        new_username = request.form.get('new_username')         
        
        if current_username is None or new_username is None:
            flash('Заполните это поле.')  
            return render_template('change_username.html', user=user)  
        
        user_from_db = User.query.filter_by(username=current_username).first()
        
        if user_from_db:
            if User.query.filter_by(username=new_username).first():
                return render_template('change_username.html', user=user, message='Такое имя уже существует.')  
            else:
                user_from_db.username = new_username
                db.session.commit()
                flash('Имя было измененно')
                session['username'] = new_username
                return redirect(url_for('profile'))
        else:
            return render_template('change_username.html', user=user, message='Имя не найденно.')  
            
    return render_template('change_username.html', user=user)  

@app.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
    user = g.user  

  
    if user is None:
        flash('Вы не вошли в систему.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form['password']
        
    
        if check_password_hash(user.password, password):
            db.session.delete(user)  
            db.session.commit()  
            session.clear()  
            flash('Ваш аккаунт был успешно удалён.', 'success')
            return redirect(url_for('login'))  
        else:
            return render_template('delete_account.html', user=user, message='Неверный пароль.')

    return render_template('delete_account.html', user=user)

@app.route('/about_us')
def us():
    brightness = request.args.get('brightness', default=100, type=int) 
    make_pink = request.args.get('make_pink', default='false')  

    if make_pink == 'true':
       filter_style = "hue-rotate(300deg) brightness(" + str(brightness) + "%)"  
    else:
        filter_style = f"brightness({brightness}%)"

    return render_template('about_us.html', user=g.user, filter_style=filter_style, brightness=brightness)

@app.route('/forum', methods=['GET', 'POST'])
def forum():
    if request.method == 'POST':
        if g.user.status == 'Забанен':
            flash('Вы не можете отправлять сообщения, так как вы забанены :(')
            return redirect(url_for('forum'))

        if 'message' in request.form:
            message_content = request.form['message']
            new_message = Message(content=message_content, user_id=g.user.id)
            db.session.add(new_message)
            db.session.commit()
            flash('Сообщение отправлено.')
        else:
            flash('Ошибка: Сообщение не может быть пустым.')

        if 'ban_user' in request.form and g.user.status == 'Администратор':
            username_to_ban = request.form['ban_user']
            user_to_ban = User.query.filter_by(username=username_to_ban).first()
            if user_to_ban:
                user_to_ban.status = 'Забанен'
                db.session.commit()
                flash(f'Пользователь {username_to_ban} был забанен.')
            else:
                flash('Пользователь не найден.')

        if 'unban_user' in request.form and g.user.status == 'Администратор':
            username_to_unban = request.form['unban_user']
            user_to_unban = User.query.filter_by(username=username_to_unban).first()
            if user_to_unban:
                user_to_unban.status = 'Участник' 
                db.session.commit()
                flash(f'Пользователь {username_to_unban} был разбанен.')
            else:
                flash('Пользователь не найден.')

    messages = Message.query.order_by(Message.timestamp.desc()).all() 
    return render_template('forum.html', messages=messages, user=g.user)



@app.route('/quiz1', methods=['GET', 'POST'])
def quiz1():
    return quiz_logic(1)  

@app.route('/quiz2', methods=['GET', 'POST'])
def quiz2():
    return quiz_logic(2)

@app.route('/quiz3', methods=['GET', 'POST'])
def quiz3():
    return quiz_logic(3)

@app.route('/quiz4', methods=['GET', 'POST'])
def quiz4():
    return quiz_logic(4)  

@app.route('/quiz5', methods=['GET', 'POST'])
def quiz5():
    return quiz_logic(5)  

@app.route('/quiz6', methods=['GET', 'POST'])
def quiz6():
    return quiz_logic(6)  

@app.route('/quiz7', methods=['GET', 'POST'])
def quiz7():
    return quiz_logic(7)  

@app.route('/quiz8', methods=['GET', 'POST'])
def quiz8():
    return quiz_logic(8)  

@app.route('/quiz9', methods=['GET', 'POST'])
def quiz9():
    return quiz_logic(9)  

@app.route('/quiz10', methods=['GET', 'POST'])
def quiz10():
 return quiz_logic(10)
def quiz_logic(quiz_number):
    user = g.user
    questions = {
    1: {  
        "text": "Изменение климата",
        "questions": [
            {
                "question": "Что является основным причиной изменения климата?",
                "options": {
                    "A": "Природные циклы",
                    "B": "Деятельность человека",
                    "C": "Изменения в солнечном излучении",
                    "D": "Ничто из вышеперечисленного"
                },
                "correct_answer": "B"
            },
            {
                "question": "Какое из следующих последствий относится к изменению климата?",
                "options": {
                    "A": "Понижение уровня моря",
                    "B": "Снижение температуры",
                    "C": "Увеличение ледников",
                    "D": "Увеличение частоты ураганов"
                },
                "correct_answer": "D"
            },
            {
                "question": "Какое из следующих действий может помочь замедлить изменение климата?",
                "options": {
                    "A": "Сжигание угля",
                    "B": "Использование солнечных панелей",
                    "C": "Автомобильные поездки",
                    "D": "Увеличение выбросов углекислого газа"
                },
                "correct_answer": "B"
            }
        ]
    },
    2: {  
        "text": "Загрязнение воздуха",
        "questions": [
            {
                "question": "Какой из следующих веществ считается загрязнителем воздуха?",
                "options": {
                    "A": "Кислород",
                    "B": "Азот",
                    "C": "Диоксид углерода",
                    "D": "Водяной пар"
                },
                "correct_answer": "C"
            },
            {
                "question": "Какое заболевание часто связано с загрязнением воздуха?",
                "options": {
                    "A": "Диабет",
                    "B": "Астма",
                    "C": "Грипп",
                    "D": "Рак кожи"
                },
                "correct_answer": "B"
            },
            {
                "question": "Как можно уменьшить загрязнение воздуха?",
                "options": {
                    "A": "Использование общественного транспорта",
                    "B": "Сжигание мусора",
                    "C": "Увеличение использования автомобилей",
                    "D": "Ничего не делать"
                },
                "correct_answer": "A"
            }
        ]
    },
    3: {  
        "text": "Устойчивое развитие",
        "questions": [
            {
                "question": "Что такое устойчивое развитие?",
                "options": {
                    "A": "Развитие, которое игнорирует окружающую среду",
                    "B": "Развитие, которое заботится о будущем",
                    "C": "Развитие, основанное на потреблении ресурсов",
                    "D": "Развитие, которое идет против прогресса"
                },
                "correct_answer": "B"
            },
            {
                "question": "Какое из следующих является примером устойчивого развития?",
                "options": {
                    "A": "Использование ископаемого топлива",
                    "B": "Сохранение лесов",
                    "C": "Переработка пластика",
                    "D": "Вариант 2 и 3"
                },
                "correct_answer": "D"
            },
            {
                "question": "Какое поведение способствует устойчивому развитию?",
                "options": {
                    "A": "Снижение потребления воды",
                    "B": "Увеличение отходов",
                    "C": "Игнорирование вопросов экологии",
                    "D": "Разрушение экосистем"
                },
                "correct_answer": "A"
            }
        ]
    },
    4: {  
        "text": "Вода",
        "questions": [
            {
                "question": "Какое из следующих действий помогает сохранять водные ресурсы?",
                "options": {
                    "A": "Промышленное загрязнение",
                    "B": "Установка водосберегающих устройств",
                    "C": "Безответственное использование воды",
                    "D": "Засорение рек"
                },
                "correct_answer": "B"
            },
            {
                "question": "Что такое водный кризис?",
                "options": {
                    "A": "Избыток воды",
                    "B": "Недостаток пресной воды",
                    "C": "Увеличение уровня моря",
                    "D": "Изменение климата"
                },
                "correct_answer": "B"
            },
            {
                "question": "Какое из следующих действий может привести к загрязнению источников воды?",
                "options": {
                    "A": "Использование удобрений",
                    "B": "Сохранение водоемов",
                    "C": "Чистка воды",
                    "D": "Создание заповедников"
                },
                "correct_answer": "A"
            }
        ]
    },
    5: {  
        "text": "Биологическое разнообразие",
        "questions": [
            {
                "question": "Почему биологическое разнообразие важно?",
                "options": {
                    "A": "Оно не имеет значения",
                    "B": "Для поддержания экосистемных услуг",
                    "C": "Для увеличения загрязнения",
                    "D": "Для уменьшения ресурсов"
                },
                "correct_answer": "B"
            },
            {
                "question": "Какое из следующих является угрозой для биологического разнообразия?",
                "options": {
                    "A": "Охрана природы",
                    "B": "Глобальное потепление",
                    "C": "Устойчивое земледелие",
                    "D": "Экосистемное восстановление"
                },
                "correct_answer": "B"
            },
            {
                "question": "Что из перечисленного способно повысить уровень биологического разнообразия?",
                "options": {
                    "A": "Вырубка лесов",
                    "B": "Создание заповедников",
                    "C": "Загрязнение океанов",
                    "D": "Строительство новых городов"
                },
                "correct_answer": "B"
            }
        ]
    },
    6: {  
        "text": "Устойчивый транспорт",
        "questions": [
            {
                "question": "Какой из следующих видов транспорта считается устойчивым?",
                "options": {
                    "A": "Автомобиль на бензине",
                    "B": "Электрический велосипед",
                    "C": "Самолет",
                    "D": "Грузовик"
                },
                "correct_answer": "B"
            },
            {
                "question": "Что такое углеродный след?",
                "options": {
                    "A": "След, оставленный людьми",
                    "B": "Количество углерода, выбрасываемого в атмосферу",
                    "C": "Следы на земле",
                    "D": "Углеродные соединения в воде"
                },
                "correct_answer": "B"
            },
            {
                "question": "Какое действие может снизить углеродный след?",
                "options": {
                    "A": "Использование личного автомобиля",
                    "B": "Частая поездка на общественном транспорте",
                    "C": "Неиспользование велосипеда",
                    "D": "Повышение использования ископаемых топлив"
                },
                "correct_answer": "B"
            }
        ]
    },
    7: {  
        "text": "Отходы и переработка",
        "questions": [
            {
                "question": "Какое из следующих является примером переработки?",
                "options": {
                    "A": "Сжигание мусора",
                    "B": "Сбор стеклянных бутылок для повторного использования",
                    "C": "Сброс отходов в океан",
                    "D": "Засорение свалки"
                },
                "correct_answer": "B"
            },
            {
                "question": "Какой из следующих методов помогает уменьшить количество отходов?",
                "options": {
                    "A": "Покупка одноразовых товаров",
                    "B": "Использование многоразовых сумок",
                    "C": "Отказ от переработки",
                    "D": "Сжигание отходов"
                },
                "correct_answer": "B"
            },
            {
                "question": "Что такое компостирование?",
                "options": {
                    "A": "Процесс разложения органических отходов",
                    "B": "Процесс сжигания отходов",
                    "C": "Процесс переработки пластика",
                    "D": "Процесс выбрасывания мусора"
                },
                "correct_answer": "A"
            }
        ]
    },
    8: {  
        "text": "Энергосбережение",
        "questions": [
            {
                "question": "Какое из следующих действий помогает экономить энергию?",
                "options": {
                    "A": "Оставлять свет включенным",
                    "B": "Использовать энергосберегающие лампы",
                    "C": "Забывать выключать электроприборы",
                    "D": "Увеличивать температуру обогревателей"
                },
                "correct_answer": "B"
            },
            {
                "question": "Что такое углеродный след?",
                "options": {
                    "A": "След, оставленный людьми",
                    "B": "Количество углерода, выбрасываемого в атмосферу",
                    "C": "Следы на земле",
                    "D": "Углеродные соединения в воде"
                },
                "correct_answer": "B"
            },
            {
                "question": "Какое из следующих действий может помочь в энергосбережении?",
                "options": {
                    "A": "Замена обычных ламп на светодиоды",
                    "B": "Использование старых приборов",
                    "C": "Увеличение потребления электроэнергии",
                    "D": "Необоснованное использование энергии"
                },
                "correct_answer": "A"
            }
        ]
    },
    9: {  
        "text": "Лесные экосистемы",
        "questions": [
            {
                "question": "Какую роль играют леса в экосистеме?",
                "options": {
                    "A": "Поглощение углекислого газа",
                    "B": "Увеличение загрязнения",
                    "C": "Уменьшение кислорода",
                    "D": "Не имеют значения"
                },
                "correct_answer": "A"
            },
            {
                "question": "Какое из следующих действий угрожает лесам?",
                "options": {
                    "A": "Засаживание деревьев",
                    "B": "Вырубка лесов",
                    "C": "Охрана природы",
                    "D": "Создание заповедников"
                },
                "correct_answer": "B"
            },
            {
                "question": "Какое из следующих действий способствует восстановлению лесов?",
                "options": {
                    "A": "Вырубка деревьев",
                    "B": "Создание заповедников",
                    "C": "Строительство новых домов",
                    "D": "Расширение сельскохозяйственных угодий"
                },
                "correct_answer": "B"
            }
        ]
    },
    10: {  
        "text": "Глобальное потепление",
        "questions": [
            {
                "question": "Что вызывает глобальное потепление?",
                "options": {
                    "A": "Солнечные циклы",
                    "B": "Человеческая деятельность",
                    "C": "Охлаждение планеты",
                    "D": "Поглощение углерода"
                },
                "correct_answer": "B"
            },
            {
                "question": "Какое из следующих последствий связано с глобальным потеплением?",
                "options": {
                    "A": "Снижение уровня моря",
                    "B": "Повышение уровня моря",
                    "C": "Увеличение ледников",
                    "D": "Снижение температуры"
                },
                "correct_answer": "B"
            },
            {
                "question": "Какое действие может помочь в борьбе с глобальным потеплением?",
                "options": {
                    "A": "Сжигание угля",
                    "B": "Снижение выбросов углерода",
                    "C": "Повышение потребления пластика",
                    "D": "Игнорирование изменений климата"
                },
                "correct_answer": "B"
            }
        ]
    }
}


    if quiz_number not in questions:
        return redirect(url_for('home'))

    quiz_data = questions[quiz_number]
    questions_list = quiz_data["questions"]
    user = get_current_user()
    top_players = User.query.order_by(User.points.desc()).limit(10).all()
    already_completed = user.quizzes_completed & (1 << (quiz_number - 1)) if user else False

    if request.method == 'POST':
        selected_answer = request.form.get('answer')
        current_question = questions_list[session['current_question']]


        if selected_answer == current_question['correct_answer']:
            session['score'] += 100  
        else:
            session['score'] -= 10  

        session['current_question'] += 1

        if session['current_question'] >= len(questions_list):
            total_questions = len(questions_list)
            score = session['score'] 

           
            if user and not already_completed:  
                user.points += score 
                user.quizzes_completed |= (1 << (quiz_number - 1))  
                db.session.commit()


            flash(f'Тест завершён! Вы набрали {score} из {total_questions * 100} очков.')
            session.pop('current_question', None)
            session.pop('score', None)

            return render_template('result.html', 
                                   score=score, 
                                   total_questions=total_questions, 
                                   user=user, 
                                   total_points=user.points) 

    if session.get('current_question') is None:
        session['current_question'] = 0
        session['score'] = 0

    current_question = questions_list[session['current_question']]
    return render_template(f'quizs/quiz{quiz_number}.html', 
                           quiz=current_question, 
                           text=quiz_data["text"], 
                           user=user,
                           already_completed=already_completed,
                           top_players=top_players)
 


@app.route('/top_list')
def top_list():
    user = get_current_user()
    users = User.query.order_by(User.points.desc()).limit(500).all()
    user_rank = None 

    if user:

        for index, u in enumerate(users):
            if u.id == user.id:
                user_rank = index + 1
                break
    return render_template('top_list.html', users=users, user=user, user_rank=user_rank) 
    


if __name__ == '__main__':
    app.run(debug=True)
