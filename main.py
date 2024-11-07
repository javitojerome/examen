from flask import Flask, render_template, request, jsonify, g, redirect, session, flash, url_for
import sqlite3

app = Flask(__name__)

app.secret_key = 'mi_clave'  # Cambia esto por una clave realmente segura
#base de datos
DATABASE = 'database.db'

def get_db():
    # Abre la conexión a la base de datos si aún no está abierta
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def create_tables():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # Asegúrate de que las comillas y la sintaxis sean correctas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS amigos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amigo_1 INTEGER NOT NULL,
                amigo_2 INTEGER NOT NULL,
                FOREIGN KEY (amigo_1) REFERENCES usuario(id),
                FOREIGN KEY (amigo_2) REFERENCES usuario(id)
            )
        ''')
        db.commit()


# Llama a create_tables una vez para crear las tablas
create_tables()

#rutas a templates 
@app.route('/index')
def register_view():
    return render_template('index.html')

# Ruta para la página de amigos
@app.route('/friends', methods=['GET', 'POST'])
def friends_view():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Si no está logueado, redirige al login

    user_id = session['user_id']  # Obtener el ID del usuario desde la sesión
    
    db = get_db()

    # Obtener todos los amigos del usuario
    query = '''
        SELECT u.id, u.first_name, u.last_name, u.email
        FROM usuario u
        JOIN amigos a ON (a.amigo_1 = u.id OR a.amigo_2 = u.id)
        WHERE a.amigo_1 = ? OR a.amigo_2 = ?
    '''
    friends = db.execute(query, (user_id, user_id)).fetchall()

    # Obtener todos los usuarios que no son amigos
    query_no_friends = '''
        SELECT id, first_name, last_name, email
        FROM usuario
        WHERE id != ? AND id NOT IN (
            SELECT amigo_1 FROM amigos WHERE amigo_1 = ? OR amigo_2 = ?
            UNION
            SELECT amigo_2 FROM amigos WHERE amigo_1 = ? OR amigo_2 = ?
        )
    '''
    no_friends = db.execute(query_no_friends, (user_id, user_id, user_id, user_id, user_id)).fetchall()

    if request.method == 'POST':
        # Agregar un amigo
        if 'add_friend' in request.form:
            new_friend_id = request.form['add_friend']
            db.execute('''
                INSERT INTO amigos (amigo_1, amigo_2) VALUES (?, ?)
            ''', (user_id, new_friend_id))
            db.commit()
            return redirect(url_for('friends_view'))

        # Eliminar un amigo
        if 'remove_friend' in request.form:
            friend_id_to_remove = request.form['remove_friend']
            db.execute('''
                DELETE FROM amigos WHERE (amigo_1 = ? AND amigo_2 = ?) OR (amigo_1 = ? AND amigo_2 = ?)
            ''', (user_id, friend_id_to_remove, friend_id_to_remove, user_id))
            db.commit()
            return redirect(url_for('friends_view'))

    return render_template('friends.html', friends=friends, no_friends=no_friends)
# Ruta para el perfil de usuario, recibe un ID como parámetro
@app.route('/user/<int:user_id>', methods=['GET'])
def user_profile(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Si no está logueado, redirige al login

    db = get_db()

    # Obtener la información del usuario
    user = db.execute('SELECT * FROM usuario WHERE id = ?', (user_id,)).fetchone()

    if not user:
        return "User not found", 404

    # Puedes devolver la información del usuario en un template
    return render_template('user.html', user=user)


#rutas para api
"""
Resumen de las Rutas
/register (POST): Registra un nuevo usuario con first_name, last_name, email y password.
/login (POST): Verifica el inicio de sesión de un usuario con email y password.
/add_friend (POST): Agrega una relación de amistad entre dos usuarios.
/remove_friend (POST): Elimina una relación de amistad entre dos usuarios.
/users (GET): Obtiene una lista de todos los usuarios registrados.
"""
@app.route('/users', methods=['GET'])
def get_users():
    db = get_db()
    users = db.execute("SELECT id, first_name, last_name, email FROM usuario").fetchall()
    user_list = [{"id": user[0], "first_name": user[1], "last_name": user[2], "email": user[3]} for user in users]
    return jsonify(user_list), 200


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']

        db = get_db()

        # Verificar si el correo ya está registrado
        user = db.execute('SELECT * FROM usuario WHERE email = ?', (email,)).fetchone()
        if user:
            flash("Email already registered. Please login.", "error")
            return redirect(url_for('register_view'))  # Redirigir para mostrar el mensaje

        # Insertar el nuevo usuario
        db.execute('''
            INSERT INTO usuario (first_name, last_name, email, password)
            VALUES (?, ?, ?, ?)
        ''', (first_name, last_name, email, password))
        db.commit()

        # Obtener el ID del usuario recién creado
        user_id = db.execute('SELECT id FROM usuario WHERE email = ?', (email,)).fetchone()[0]

        # Almacenar el ID del usuario en la sesión
        session['user_id'] = user_id

        # Redirigir a la página de amigos después del registro
        return redirect(url_for('friends_view'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('''
            SELECT id, first_name, last_name, email, password 
            FROM usuario WHERE email = ?
        ''', (email,)).fetchone()
        print(user)
        # Verificar si el usuario existe y si la contraseña coincide
        if user[-1] == password:
            # Si las credenciales son correctas, guardamos el ID del usuario en la sesión
            session['user_id'] = user[0]
            session['first_name'] = user[1]
            session['last_name'] = user[2]
            
            flash('Login successful!', 'success')
            return redirect(url_for('friends_view'))  # Redirigir a una página de usuario, como el dashboard
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('index.html')

#amigos
@app.route('/friends/<int:user_id>', methods=['GET'])
def get_friends(user_id):
    db = get_db()
    # Seleccionar amigos donde el usuario es amigo_1 o amigo_2
    query = '''
    SELECT u.id, u.first_name, u.last_name, u.email
    FROM amigos a
    JOIN usuario u ON (u.id = a.amigo_1 OR u.id = a.amigo_2)
    WHERE (a.amigo_1 = ? OR a.amigo_2 = ?) AND u.id != ?;
    '''
    
    # Ejecutar la consulta para obtener los amigos
    friends = db.execute(query, (user_id, user_id, user_id)).fetchall()
    
    # Si no tiene amigos, retornar un mensaje
    if not friends:
        return jsonify({"message": "You have no friends yet."}), 404
    
    # Convertir la lista de amigos a un formato de respuesta JSON
    friends_list = [{"id": friend[0], "first_name": friend[1], "last_name": friend[2], "email": friend[3]} for friend in friends]
    
    return jsonify(friends_list), 200


@app.route('/friends/add', methods=['POST'])
def add_friend():
    data = request.json
    amigo_1 = data['amigo_1']  # ID del usuario que agrega al amigo
    amigo_2 = data['amigo_2']  # ID del usuario que se agrega como amigo
    
    db = get_db()

    # Verifica si la relación de amistad ya existe (para evitar duplicados)
    existing_friendship = db.execute("SELECT * FROM amigos WHERE (amigo_1 = ? AND amigo_2 = ?) OR (amigo_1 = ? AND amigo_2 = ?)",
                                     (amigo_1, amigo_2, amigo_2, amigo_1)).fetchone()

    if existing_friendship:
        return jsonify({"error": "This friendship already exists."}), 400
    
    # Inserta la relación de amistad
    db.execute("INSERT INTO amigos (amigo_1, amigo_2) VALUES (?, ?)", (amigo_1, amigo_2))
    db.execute("INSERT INTO amigos (amigo_1, amigo_2) VALUES (?, ?)", (amigo_2, amigo_1))  # Relación bidireccional
    db.commit()
    
    return jsonify({"message": "Friend added successfully!"}), 201

#eliminar amigo
@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    data = request.json
    amigo_1 = data['amigo_1']  # ID del usuario que desea eliminar al amigo
    amigo_2 = data['amigo_2']  # ID del amigo que se desea eliminar
    
    db = get_db()

    # Elimina la relación de amistad
    db.execute("DELETE FROM amigos WHERE (amigo_1 = ? AND amigo_2 = ?) OR (amigo_1 = ? AND amigo_2 = ?)",
               (amigo_1, amigo_2, amigo_2, amigo_1))
    db.commit()
    
    return jsonify({"message": "Friend removed successfully!"}), 200







if __name__ == '__main__':
    app.run(debug=True)