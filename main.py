from flask import Flask, render_template

app = Flask(__name__)


@app.route('/index')
def register():
    return render_template('index.html')

# Ruta para la página de amigos
@app.route('/friends')
def friends():
    return render_template('friends.html')

# Ruta para el perfil de usuario, recibe un ID como parámetro
@app.route('/user/<int:user_id>')
def user_profile(user_id):
    return render_template('user.html', user_id=user_id)

if __name__ == '__main__':
    app.run(debug=True)