from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

import unicodedata
import os

app = Flask(__name__)

#ログイン管理システム
login_maneger = LoginManager()
login_maneger.init_app(app)



db  = SQLAlchemy()
if app.debug:
    app.config["SECRET_KEY"] = os.urandom(24)
    DB_INFO = {
        'user':'postgres',
        'password':'Ha121211',
        'host':'localhost',
        'name':'postgres',
    }
    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg://{user}:{password}@{host}/{name}'.format(**DB_INFO)
else:
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL').replace('postgres://', 'postgresql+psycopg://')
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
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
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            action = request.form.get('action')

            if action == 'to_signup':
                return redirect("/signup")

            if not username or not password:
                return redirect(url_for('login', msg="ユーザ名とパスワードを入力してください"))

            user = User.query.filter_by(username=username).first()
            if user is None or not check_password_hash(user.password, password):
                return redirect(url_for('login', msg="ユーザ名、パスワードが違います"))

            login_user(user)
            return redirect('/inv')
        elif request.method == 'GET':
            return render_template('login.html', msg=msg)
    except Exception as e:
        return redirect(url_for('login', msg=f"エラーが発生しました: {str(e)}"))


#在庫管理、発注
@app.route("/inv", methods=['GET', 'POST'])
def inv():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))  # ログインページにリダイレクト

    try:
        raw_posts = Inventry.query.filter_by(user=current_user.username).order_by(Inventry.groop, Inventry.name, Inventry.limit).all()
        seen_names = set()  # 品名の重複を避けるためのセット
        posts = []

        for post in raw_posts:
            is_expired = post.limit < datetime.now()  # 賞味期限のチェック
            if post.name not in seen_names:
                posts.append({
                    "id": post.id, "groop": post.groop, "name": post.name,
                    "num": post.num, "limit": post.limit.strftime('%Y-%m-%d'),
                    "is_first": True, "is_expired": is_expired
                })
                seen_names.add(post.name)
            else:
                posts.append({
                    "id": post.id, "groop": post.groop, "name": post.name,
                    "num": post.num, "limit": post.limit.strftime('%Y-%m-%d'),
                    "is_first": False, "is_expired": is_expired
                })

        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'to_menu':
                return redirect("/menu")
            elif action == 'to_compare':
                return redirect("/compare")

            # リクエストで来た情報の取得
            name = request.form.get('name')
            num = request.form.get('num')
            limit = request.form.get('limit')
            groop = request.form.get('groop')

            if not all([name, num, limit, groop]):
                flash("全てのフィールドを入力してください", 'error')
                return redirect(url_for('inv'))

            num = unicodedata.normalize('NFKC', num)

            try:
                # 情報の保存
                post = Inventry(groop=groop, name=name, num=num, limit=limit, user=current_user.username)
                db.session.add(post)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(f"データベースエラーが発生しました: {str(e)}", 'error')
                return redirect(url_for('inv'))

            return redirect(url_for('inv'))
        elif request.method == 'GET':
            return render_template('inv.html', posts=posts)

    except Exception as e:
        flash(f"エラーが発生しました: {str(e)}", 'error')
        return redirect(url_for('inv'))


#メニュー管理画面
@app.route("/menu", methods=['GET', 'POST'])
def menu():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))  # ログインページにリダイレクト
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
            ingredient_quantity = unicodedata.normalize('NFKC', ingredient_quantity)
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
def compare():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))  # ログインページにリダイレクト
    today = datetime.today()
    next_day = today + timedelta(days=1)
    next_weekday = next_day.strftime('%A')
    expiration_date = today + timedelta(days=3)  # 賞味期限は3日後

    # 予測データ取得
    next_day_predictions = (
        db.session.query(Prediction)
        .filter(Prediction.user == current_user.username, Prediction.weekday == next_weekday)
        .order_by(Prediction.groop, Prediction.name)
        .all()
    )

    # 予測データと在庫の比較
    seen_names = set()
    posts = []
    for prediction in next_day_predictions:
        if prediction.name not in seen_names:
            inventories = Inventry.query.filter_by(user=current_user.username, name=prediction.name).all()
            total_quantity = sum([inv.num for inv in inventories])  # 同じ品名の在庫数を合計
            posts.append({
                "groop": prediction.groop,
                "name": prediction.name,
                "prediction_num": prediction.num,
                "total_quantity": total_quantity,
                "inventories": inventories
            })
            seen_names.add(prediction.name)

    # 必要な材料の計算
    material_comparison = []
    for prediction in next_day_predictions:
        menu = Menu.query.filter_by(name=prediction.name).first()
        if menu:
            for ingredient in menu.ingredients:
                required_quantity = int(ingredient.quantity) * prediction.num
                inventories = Inventry.query.filter_by(user=current_user.username, name=ingredient.name).all()
                inventory_quantity = sum([inv.num for inv in inventories])  # 同じ品名の在庫数を合計
                shortage = max(0, required_quantity - inventory_quantity)

                material_comparison.append({
                    "menu_name": menu.name,
                    "material_name": ingredient.name,
                    "required_quantity": required_quantity,
                    "inventory_quantity": inventory_quantity,
                    "shortage": shortage,
                    "groop": inventories[0].groop if inventories else "材料"  # groopを参照
                })

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'to_menu':
            return redirect("/menu")
        elif action == 'to_inv':
            return redirect("/inv")
        elif action == 'add_inventory':
            material_name = request.form.get('material_name')
            shortage = int(request.form.get('shortage'))
            groop = request.form.get('groop')

            try:
                # 在庫に新たに追加
                new_inventory = Inventry(
                    user=current_user.username,
                    groop=groop,  # 参照したgroopを格納
                    name=material_name,
                    num=shortage,
                    limit=expiration_date
                )
                db.session.add(new_inventory)
                db.session.commit()
                flash(f"{material_name}の不足分を追加しました。", 'success')
            except Exception as e:
                db.session.rollback()
                flash(f"在庫追加中にエラーが発生しました: {str(e)}", 'error')

            return redirect("/compare")

        # 予測データ追加
        selected_day = request.form.get('options')
        groop = request.form.get('groop')
        name = request.form.get('name')
        num = int(unicodedata.normalize('NFKC', request.form.get('num')))

        new_prediction = Prediction(
            groop=groop, name=name, num=num,
            user=current_user.username, weekday=selected_day
        )
        db.session.add(new_prediction)
        db.session.commit()
        return redirect("/compare")

    return render_template(
        'compare.html',
        posts=posts,
        day=next_day,
        next_day_predictions=next_day_predictions,
        material_comparison=material_comparison
    )



#在庫データ更新画面
@app.route("/<int:post_id>/update", methods=['GET', 'POST'])
def update(post_id):    
    if not current_user.is_authenticated:
        return redirect(url_for('login'))  # ログインページにリダイレクト
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
def menuupdate(post_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))  # ログインページにリダイレクト
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
def delete(post_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))  # ログインページにリダイレクト
    post = Inventry.query.get(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect("/inv")

#menu削除機能
@app.route("/<int:post_id>/menudelete")
def menudelete(post_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))  # ログインページにリダイレクト
    post = Menu.query.get(post_id)

    # 関連する材料を削除
    for ingredient in post.ingredients:
        db.session.delete(ingredient)

    db.session.delete(post)
    db.session.commit()
    return redirect("/menu")

#サインアップページ
@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # ユーザ名が既に使用されていないか確認
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("このユーザ名は既に使用されています。別のユーザ名を選んでください。", 'error')
            return redirect(url_for('signup'))

        hashed_pass = generate_password_hash(password)
        user = User(username=username, password=hashed_pass)

        try:
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"データベースエラーが発生しました: {str(e)}", 'error')
            return redirect(url_for('signup'))

        flash("ユーザ登録が完了しました。ログインしてください。", 'success')
        return redirect('/')
    elif request.method == 'GET':
        return render_template('signup.html')

    
#ログアウト
@app.route("/logout")
def logout():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))  # ログインページにリダイレクト
    logout_user()
    return redirect("/")