from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

import unicodedata
import os

app = Flask(__name__)

#一旦ランダム後で書き換える
app.config["SECRET_KEY"] = os.urandom(24)

#ログイン管理システム
login_maneger = LoginManager()
login_maneger.init_app(app)

db  = SQLAlchemy()
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://postgres:Ha121211@localhost/postgres'
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
db.init_app(app)
migrate = Migrate(app,db)

class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    groop = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    user = db.Column(db.String(100), nullable=False)
    ingredients = db.relationship('Ingredient', backref='menu', lazy=True)
    
class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) 
    quantity = db.Column(db.String(50), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu.id'), nullable=False) 

class Inventry(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user = db.Column(db.String, nullable = False)
    groop = db.Column(db.String, nullable = False)
    name = db.Column(db.String, nullable = False)
    num = db.Column(db.Integer, nullable = False)
    limit = db.Column(db.DateTime, nullable = False)

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user = db.Column(db.String, nullable = False)
    weekday = db.Column(db.String, nullable = False)
    groop = db.Column(db.String, nullable = False)
    name = db.Column(db.String, nullable = False)
    num = db.Column(db.Integer, nullable = False)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key= True)
    username = db.Column(db.String, nullable = False, unique = True)
    password = db.Column(db.String, nullable = False)
    
#現在のユーザを識別する関数
@login_maneger.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



#ログイン画面
@app.route("/", methods=['GET', 'POST'])
def login():
    msg = request.args.get('msg', '')
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        action = request.form.get('action')
        if action == 'to_signup':
            return redirect("/signup")
        if user is None or not check_password_hash(user.password, password):
            return redirect(url_for('login', msg="ユーザ名、パスワードが違います"))
        login_user(user)
        return redirect('/inv')
    elif request.method == 'GET':
        return render_template('login.html', msg=msg)



#在庫管理、発注
@app.route("/inv", methods=['GET', 'POST'])
@login_required
def inv():
    raw_posts = Inventry.query.filter_by(user=current_user.username).order_by(Inventry.groop, Inventry.name).all()
    seen_names = set()  # 品名の重複を避けるためのセット
    posts = []

    for post in raw_posts:
        # 品名が初めて出現した場合のみフラグを追加
        if post.name not in seen_names:
            posts.append({"id": post.id, "groop": post.groop, "name": post.name, "num": post.num, "limit": post.limit.strftime('%Y-%m-%d'), "is_first": True})
            seen_names.add(post.name)
        else:
            posts.append({"id":post.id, "groop": post.groop, "name": post.name, "num": post.num, "limit": post.limit.strftime('%Y-%m-%d'), "is_first": False})

    #methodの判別
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'to_menu':
            return redirect("/menu")
        elif action == 'to_compare':
            return redirect("/compare")
        #リクエストで来た情報の取得
        name = request.form.get('name')
        num = request.form.get('num')
        limit = request.form.get('limit')
        groop = request.form.get('groop')
        
        num = unicodedata.normalize('NFKC', num)
        #情報の保存
        post = Inventry(groop = groop, name=name, num=num, limit=limit, user = current_user.username)
        db.session.add(post)
        db.session.commit()
        return redirect("/inv")
    elif request.method == 'GET':
        return render_template('inv.html',posts = posts)
    
    
    
@app.route("/menu", methods=['GET', 'POST'])
@login_required
def menu():
    raw_posts = Menu.query.filter_by(user=current_user.username).order_by(Menu.groop, Menu.name).all()
    seen_names = set()
    posts = []

    for post in raw_posts:
        if post.name not in seen_names:
            posts.append({"id": post.id, "groop": post.groop, "name": post.name, "ingre": post.ingredients, "is_first": True})
            seen_names.add(post.name)
        else:
            posts.append({"id": post.id, "groop": post.groop, "name": post.name, "ingre": post.ingredients, "is_first": False})

    if request.method == 'POST':
        # フォームデータの取得
        action = request.form.get('action')

        if action == 'to_inv':
            return redirect("/inv")
        elif action == 'to_compare':
            return redirect("/compare")
        groop = request.form.get('groop')
        name = request.form.get('name')
        ingredient_count = int(request.form.get('ingredient_count', 0))

        # 材料データを取得
        ingredients = []
        for i in range(ingredient_count):
            ingredient_name = request.form.get(f'ingredients[{i}][name]')
            ingredient_quantity = request.form.get(f'ingredients[{i}][quantity]')
            if ingredient_name and ingredient_quantity:
                ingredients.append({'name': ingredient_name, 'quantity': ingredient_quantity})

        print(f"材料リスト: {ingredients}")  # デバッグ

        # Menuを作成
        menu = Menu(groop=groop, name=name, user=current_user.username)
        db.session.add(menu)
        db.session.flush()  # `menu.id`を取得するためにflush

        print(f"Menu ID: {menu.id}")  # デバッグ

        # 材料を保存
        for ingredient in ingredients:
            db.session.add(Ingredient(
                name=ingredient['name'],
                quantity=ingredient['quantity'],
                menu_id=menu.id
            ))

        db.session.commit()
        return redirect("/menu")

    elif request.method == 'GET':
        return render_template('menu.html', posts=posts)




#比較画面
@app.route("/compare", methods=['GET', 'POST'])
@login_required
def compare():
    today = datetime.today()
    next_day = today + timedelta(days=1)
    next_weekday = next_day.strftime('%A')

    # PredictionとInventryをJOINして取得
    raw_posts = (
        db.session.query(Prediction)
        .join(Inventry, (Prediction.name == Inventry.name) & (Prediction.user == Inventry.user))
        .filter(Prediction.user == current_user.username, Prediction.weekday == next_weekday)
        .order_by(Inventry.groop, Inventry.name)
        .all()
    )

    seen_names = set()  # 品名の重複を避けるためのセット
    posts = []

    # 重複を避けてデータを整形
    for post in raw_posts:
        if post.name not in seen_names:
            inventories = Inventry.query.filter_by(user=current_user.username, name=post.name).all()
            posts.append({
                "groop": post.groop,
                "name": post.name,
                "prediction_num": post.num,
                "inventories": inventories
            })
            seen_names.add(post.name)

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'to_menu':
            return redirect("/menu")
        elif action == 'to_inv':
            return redirect("/inv")
        
        selected_day = request.form.get('options')      
        groop = request.form.get('groop')
        name = request.form.get('name')
        num = request.form.get('num')
        num = unicodedata.normalize('NFKC', num)

        # 新しいPredictionを追加
        post = Prediction(
            groop=groop, name=name, num=num,
            user=current_user.username, weekday=selected_day
        )
        db.session.add(post)
        db.session.commit()
        return redirect("/compare")

    elif request.method == 'GET':
        return render_template('compare.html', posts=posts, day=next_day)

        



#在庫データ更新画面
@app.route("/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update(post_id):    
    post = Inventry.query.get(post_id)
    if request.method == "POST":
        post.name = request.form.get('name')
        num = request.form.get('num')
        num = unicodedata.normalize('NFKC', num)
        post.num = num
        post.limit = request.form.get('limit')
        db.session.commit()
        return redirect("/inv")
    elif request.method == "GET":
        return render_template("update.html",post=post)
    
#メニューデータ更新画面
@app.route("/<int:post_id>/menuupdate", methods=['GET', 'POST'])
@login_required
def menuupdate(post_id):
    post = Menu.query.get(post_id)
    if request.method == "POST":
        # メニューの基本情報を更新
        post.groop = request.form.get('groop')
        post.name = request.form.get('name')

        # 既存の材料を取得
        existing_ingredients = {ingredient.id: ingredient for ingredient in post.ingredients}

        # 材料の更新と追加処理
        i = 0
        while True:
            ingredient_id = request.form.get(f'ingredients[{i}][id]')
            ingredient_name = request.form.get(f'ingredients[{i}][name]')
            ingredient_quantity = request.form.get(f'ingredients[{i}][quantity]')
            i += 1

            # ループ終了条件：フォームにこれ以上の材料データがない場合
            if not ingredient_name and not ingredient_quantity:
                break

            if ingredient_id and ingredient_id != "0":  # 既存材料の更新
                ingredient_id = int(ingredient_id)
                if ingredient_id in existing_ingredients:
                    ingredient = existing_ingredients.pop(ingredient_id)
                    ingredient.name = ingredient_name
                    ingredient.quantity = ingredient_quantity
            else:  # 新規材料の追加
                new_ingredient = Ingredient(
                    name=ingredient_name,
                    quantity=ingredient_quantity,
                    menu_id=post.id
                )
                db.session.add(new_ingredient)

        # 削除される材料を処理
        for ingredient in existing_ingredients.values():
            db.session.delete(ingredient)

        db.session.commit()
        return redirect("/menu")

    elif request.method == "GET":
        return render_template("menuupdate.html", post=post)


#在庫削除機能
@app.route("/<int:post_id>/delete")
@login_required
def delete(post_id):
    post = Inventry.query.get(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect("/inv")


#menu削除機能
@app.route("/<int:post_id>/menudelete")
@login_required
def menudelete(post_id):
    post = Menu.query.get(post_id)

    # 関連する材料を削除
    for ingredient in post.ingredients:
        db.session.delete(ingredient)

    db.session.delete(post)
    db.session.commit()
    return redirect("/menu")



#サインアップページ
@app.route("/signup", methods = ['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User(username=username,password=password)
        password = request.form.get('password')
        hashed_pass = generate_password_hash(password)
        user = User(username=username, password=hashed_pass)
        db.session.add(user)
        db.session.commit()
        return redirect('/')
    elif request.method == 'GET':
        return render_template('signup.html')
    
    

#ログアウト
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")