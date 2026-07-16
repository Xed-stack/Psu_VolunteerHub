"""
PSU Volunteer Hub - Entry Point
=================================
Application entry point that creates and runs the Flask application.
"""
from app import create_app

app = create_app()

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Capture form values submitted by the user
        email = request.form.get('email')
        password = request.form.get('password')
        account_type = request.form.get('account_type')
        campus = request.form.get('campus')

        # Capture specific volunteer details if applicable
        volunteer_type = request.form.get(
            'volunteer_type')  # Student/Faculty/Staff
        id_number = request.form.get('id_number')

        # lagay dito yung sqalchemy insetion logic

        return redirect(url_for('home'))

    return render_template('Signup.html')


if __name__ == '__main__':
    app.run(debug=True)
