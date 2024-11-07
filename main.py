from flask import Flask, render_template, request, jsonify, g
import sqlite3

app = Flask(__name__)


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
def register_vie():
    return render_template('index.html')

# Ruta para la página de amigos
@app.route('/friends')
def friends_view():
    return render_template('friends.html')

# Ruta para el perfil de usuario, recibe un ID como parámetro
@app.route('/user/<int:user_id>')
def user_profile_view(user_id):
    return render_template('user.html', user_id=user_id)


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


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    first_name = data['first_name']
    last_name = data['last_name']
    email = data['email']
    password = data['password']
    
    db = get_db()
    try:
        db.execute("INSERT INTO usuario (first_name, last_name, email, password) VALUES (?, ?, ?, ?)", 
                   (first_name, last_name, email, password))
        db.commit()
        return jsonify({"message": "User registered successfully!"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists."}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data['email']
    password = data['password']
    
    db = get_db()
    user = db.execute("SELECT * FROM usuario WHERE email = ? AND password = ?", (email, password)).fetchone()
    
    if user:
        return jsonify({"message": "Login successful!"}), 200
    else:
        return jsonify({"error": "Invalid email or password."}), 401

#agregar amigo
@app.route('/add_friend', methods=['POST'])
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