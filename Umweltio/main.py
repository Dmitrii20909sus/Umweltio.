from flask import Flask, render_template, redirect, request, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import timedelta
import os

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
    profile_picture = db.Column(db.String(200), default='profile_pics/default_profile.png', nullable=True)
    points = db.Column(db.Integer, default=0)
    correct_answers = db.Column(db.Integer, default=0)
    quizzes_completed = db.Column(db.Integer, default=0)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    correct_answer = db.Column(db.String(255), nullable=False)
    option_a = db.Column(db.String(255), nullable=False)
    option_b = db.Column(db.String(255), nullable=False)
    option_c = db.Column(db.String(255), nullable=False)
    option_d = db.Column(db.String(255), nullable=False)

with app.app_context():
    db.create_all()

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=7) 

@app.route('/')
def home():
    user = get_current_user()
    brightness_value = request.args.get('brightness', default=100, type=int)
    return render_template('index.html', user=user)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        flash('Пожалуйста, войдите в систему, чтобы получить доступ к этой странице.', 'warning')
        return redirect(url_for('login'))

    user = get_current_user()
    
    if request.method == 'POST':
        if 'file' not in request.files or request.files['file'].filename == '':
            return render_template('profile.html', user=user, message='Файл не выбран')

        file = request.files['file']
        filename = secure_filename(file.filename)  
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        user.profile_picture = f'profile_pics/{filename}'  
        db.session.commit()
        return render_template('profile.html', user=user, message='Фото профиля было изменёно')
    
    return render_template('profile.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']  

        if User.query.filter_by(username=username).first():
            return render_template('register.html', message='Такой пользователь уже существует!')

        new_user = User(username=username, 
                        password=generate_password_hash(password, method='pbkdf2:sha256'), 
                        email=email)  
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login')) 
    return render_template('register.html')

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
            return render_template('login.html', message='Неправильное имя или пароль')
    
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        session.pop('username', None)
        session.pop('user_id', None) 
        flash('Вы вышли из аккаунта ', 'info')  
        return redirect(url_for('home'))
    
    user = get_current_user()
    return render_template('confirm_logout.html', user=user)  

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    user = get_current_user() 
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
    if request.method == 'POST':
        current_email = request.form.get('current_email')
        new_email = request.form.get('new_email')

        
        if current_email and new_email:
            user = User.query.filter_by(email=current_email).first()

            if user:
                user.email = new_email
                db.session.commit()
                flash('Почта была изменена')
                session['email'] = new_email  
                return redirect(url_for('profile'))
            else :
                return render_template('change_email.html', user=user, message='Почта не найдена.')
    user = get_current_user()   
    return render_template('change_email.html', user=user)

@app.route('/change_username', methods=['GET', 'POST'])
def change_username():
    user = get_current_user() 
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
    
@app.route('/about_us')
def us():
    user = get_current_user()
    brightness = request.args.get('brightness', default=100, type=int) 
    make_pink = request.args.get('make_pink', default='false')  

    if make_pink == 'true':
       filter_style = "hue-rotate(300deg) brightness(" + str(brightness) + "%)"  
    else:
        filter_style = f"brightness({brightness}%)"

    return render_template('about_us.html', user=user, filter_style=filter_style, brightness=brightness)

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
    questions = {
    1: {  
        "text": "Изменение климата — это долгосрочные изменения температур и погодных условий на Земле. Это явление, которое наблюдается на протяжении веков, но в последнее время оно усилилось из-за человеческой деятельности. Увеличение концентрации парниковых газов в атмосфере приводит к глобальному потеплению, которое оказывает серьезное влияние на климат.",
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
        "text": "Загрязнение воздуха — это серьезная проблема, которая затрагивает здоровье человека и окружающую среду. Основные источники загрязнения воздуха включают автомобильный транспорт, промышленность и сжигание ископаемых видов топлива. Загрязненный воздух может вызывать множество заболеваний, включая астму и сердечно-сосудистые заболевания.",
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
        "text": "Устойчивое развитие — это концепция, которая предполагает удовлетворение потребностей настоящего без ущерба для будущих поколений. Она требует изменения нашего отношения к ресурсам и среды обитания. Устойчивое развитие охватывает такие аспекты, как экономическая, социальная и экологическая устойчивость.",
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
                    "D": "Оба B и C"
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
        "text": "Вода является одним из самых ценных ресурсов на Земле, и её охрана имеет решающее значение для здоровья экосистем. Вода используется для питья, сельского хозяйства и промышленности. Каждый должен заботиться о сохранении воды и использовать её разумно, чтобы избежать водного кризиса.",
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
        "text": "Биологическое разнообразие включает в себя все живые организмы на планете и их взаимодействия. Сохранение биологического разнообразия имеет важное значение для поддержания экосистем и их функций. Угроза исчезновения видов представляет собой серьезную проблему, требующую нашего внимания.",
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
        "text": "Устойчивый транспорт включает в себя различные способы передвижения, которые минимизируют воздействие на окружающую среду. Это включает в себя использование общественного транспорта, велосипедов и пешие прогулки. Устойчивый транспорт помогает снизить выбросы углекислого газа и уменьшить загрязнение.",
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
        "text": "Управление отходами и переработка имеют важное значение для сокращения негативного влияния на окружающую среду. Эффективные стратегии управления отходами помогают снизить количество отходов, поступающих на свалки, и уменьшают загрязнение. Переработка помогает сохранить ресурсы и снижает выбросы углерода.",
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
        "text": "Энергосбережение — это эффективный способ сокращения расхода энергии и уменьшения углеродного следа. Это включает в себя использование энергоэффективных устройств и сокращение потребления электроэнергии. Энергосбережение помогает не только сэкономить деньги, но и защитить окружающую среду.",
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
        "text": "Леса являются важными экосистемами, которые поддерживают разнообразие видов и обеспечивают множество экосистемных услуг. Леса помогают очищать воздух, обеспечивают кислород и являются домом для многих животных и растений. Защита лесов имеет решающее значение для сохранения природы.",
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
        "text": "Глобальное потепление — это явление, связанное с увеличением средней температуры Земли. Оно вызвано выбросами парниковых газов, таких как углекислый газ и метан. Глобальное потепление приводит к серьезным последствиям, включая изменение климата, повышение уровня моря и изменение экосистем.",
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
