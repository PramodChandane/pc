from flask import Flask, render_template, request, redirect, session, flash, jsonify
import os
from datetime import timedelta  # used for setting session timeout
import pandas as pd
import plotly
import plotly.express as px
import json
import warnings
import support
import pickle
import yfinance as yf
from rl_agent import RLAgent

warnings.filterwarnings("ignore")

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route('/')
def login():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=15)
    if 'user_id' in session:  # if logged-in
        flash("Already a user is logged-in!")
        return redirect('/home')
    else:  # if not logged-in
        return render_template("login.html")


@app.route('/login_validation', methods=['POST'])
def login_validation():
    if 'user_id' not in session:  # if user not logged-in
        email = request.form.get('email')
        passwd = request.form.get('password')
        query = """SELECT * FROM user_login WHERE email LIKE '{}' AND password LIKE '{}'""".format(email, passwd)
        users = support.execute_query("search", query)
        if len(users) > 0:  # if user details matched in db
            session['user_id'] = users[0][0]
            return redirect('/home')
        else:  # if user details not matched in db
            flash("Invalid email and password!")
            return redirect('/')
    else:  # if user already logged-in
        flash("Already a user is logged-in!")
        return redirect('/home')


@app.route('/reset', methods=['POST'])
def reset():
    if 'user_id' not in session:
        email = request.form.get('femail')
        pswd = request.form.get('pswd')
        userdata = support.execute_query('search', """select * from user_login where email LIKE '{}'""".format(email))
        if len(userdata) > 0:
            try:
                query = """update user_login set password = '{}' where email = '{}'""".format(pswd, email)
                support.execute_query('insert', query)
                flash("Password has been changed!!")
                return redirect('/')
            except:
                flash("Something went wrong!!")
                return redirect('/')
        else:
            flash("Invalid email address!!")
            return redirect('/')
    else:
        return redirect('/home')


@app.route('/register')
def register():
    if 'user_id' in session:  # if user is logged-in
        flash("Already a user is logged-in!")
        return redirect('/home')
    else:  # if not logged-in
        return render_template("register.html")


@app.route('/registration', methods=['POST'])
def registration():
    if 'user_id' not in session:  # if not logged-in
        name = request.form.get('name')
        email = request.form.get('email')
        passwd = request.form.get('password')
        if len(name) > 5 and len(email) > 10 and len(passwd) > 5:  # if input details satisfy length condition
            try:
                query = """INSERT INTO user_login(username, email, password) VALUES('{}','{}','{}')""".format(name,
                                                                                                              email,
                                                                                                              passwd)
                support.execute_query('insert', query)

                user = support.execute_query('search',
                                             """SELECT * from user_login where email LIKE '{}'""".format(email))
                session['user_id'] = user[0][0]  # set session on successful registration
                flash("Successfully Registered!!")
                return redirect('/home')
            except:
                flash("Email id already exists, use another email!!")
                return redirect('/register')
        else:  # if input condition length not satisfy
            flash("Not enough data to register, try again!!")
            return redirect('/register')
    else:  # if already logged-in
        flash("Already a user is logged-in!")
        return redirect('/home')


@app.route('/contact')
def contact():
    return render_template("contact.html")


@app.route('/feedback', methods=['POST'])
def feedback():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    sub = request.form.get("sub")
    message = request.form.get("message")
    flash("Thanks for reaching out to us. We will contact you soon.")
    return redirect('/')


@app.route('/home')
def home():
    if 'user_id' in session:  # if user is logged-in
        query = """select * from user_login where user_id = {} """.format(session['user_id'])
        userdata = support.execute_query("search", query)

        table_query = """select * from user_expenses where user_id = {} order by pdate desc""".format(
            session['user_id'])
        table_data = support.execute_query("search", table_query)
        df = pd.DataFrame(table_data, columns=['#', 'User_Id', 'Date', 'Expense', 'Amount', 'Note'])

        df = support.generate_df(df)
        try:
            earning, spend, invest, saving = support.top_tiles(df)
        except:
            earning, spend, invest, saving = 0, 0, 0, 0

        try:
            bar, pie, line, stack_bar = support.generate_Graph(df)
        except:
            bar, pie, line, stack_bar = None, None, None, None
        try:
            monthly_data = support.get_monthly_data(df, res=None)
        except:
            monthly_data = []
        try:
            card_data = support.sort_summary(df)
        except:
            card_data = []

        try:
            goals = support.expense_goal(df)
        except:
            goals = []
        try:
            size = 240
            pie1 = support.makePieChart(df, 'Earning', 'Month_name', size=size)
            pie2 = support.makePieChart(df, 'Spend', 'Day_name', size=size)
            pie3 = support.makePieChart(df, 'Investment', 'Year', size=size)
            pie4 = support.makePieChart(df, 'Saving', 'Note', size=size)
            pie5 = support.makePieChart(df, 'Saving', 'Day_name', size=size)
            pie6 = support.makePieChart(df, 'Investment', 'Note', size=size)
        except:
            pie1, pie2, pie3, pie4, pie5, pie6 = None, None, None, None, None, None
        return render_template('home.html',
                               user_name=userdata[0][1],
                               df_size=df.shape[0],
                               df=jsonify(df.to_json()),
                               earning=earning,
                               spend=spend,
                               invest=invest,
                               saving=saving,
                               monthly_data=monthly_data,
                               card_data=card_data,
                               goals=goals,
                               table_data=table_data,
                               bar=bar,
                               line=line,
                               stack_bar=stack_bar,
                               pie1=pie1,
                               pie2=pie2,
                               pie3=pie3,
                               pie4=pie4,
                               pie5=pie5,
                               pie6=pie6,
                               )
    else:  # if not logged-in
        return redirect('/')


@app.route('/home/add_expense', methods=['POST'])
def add_expense():
    if 'user_id' in session:
        user_id = session['user_id']
        if request.method == 'POST':
            date = request.form.get('e_date')
            expense = request.form.get('e_type')
            amount = request.form.get('amount')
            notes = request.form.get('notes')
            try:
                query = """insert into user_expenses (user_id, pdate, expense, amount, pdescription) values 
                ({}, '{}','{}',{},'{}')""".format(user_id, date, expense, amount, notes)
                support.execute_query('insert', query)
                flash("Saved!!")
            except:
                flash("Something went wrong.")
                return redirect("/home")
            return redirect('/home')
    else:
        return redirect('/')


@app.route('/analysis')
def analysis():
    if 'user_id' in session:  # if already logged-in
        # Query to get user data
        query = """SELECT * FROM user_login WHERE user_id = {}""".format(session['user_id'])
        userdata = support.execute_query('search', query)
        
        # Query to get user's expenses
        query2 = """SELECT pdate, expense, pdescription, amount FROM user_expenses WHERE user_id = {}""".format(session['user_id'])
        data = support.execute_query('search', query2)
        
        # Converting data to DataFrame
        df = pd.DataFrame(data, columns=['Date', 'Expense', 'Note', 'Amount(₹)'])
        
        # Assuming this function modifies the DataFrame in some way (e.g., for date formatting)
        df = support.generate_df(df)
        
        if df.shape[0] > 0:  # If there is data available to analyze
            # Creating visualizations
            pie = support.meraPie(df=df, names='Expense', values='Amount(₹)', hole=0.7, hole_text='Expense',
                                  hole_font=20, height=180, width=180, margin=dict(t=1, b=1, l=1, r=1))
            
            df2 = df.groupby(['Note', 'Expense']).sum(numeric_only=True).reset_index()[['Expense', 'Note', 'Amount(₹)']]
            bar = support.meraBarChart(df=df2, x='Note', y='Amount(₹)', color='Expense', height=180, x_label="Category",
                                       show_xtick=False)
            
            line = support.meraLine(df=df, x='Date', y='Amount(₹)', color='Expense', slider=False, show_legend=False,
                                    height=180)
            
            scatter = support.meraScatter(df, 'Date', 'Amount(₹)', 'Expense', 'Amount(₹)', slider=False)
            
            heat = support.meraHeatmap(df, 'Day_name', 'Month_name', height=200, title="Transaction count Day vs Month")
            
            # Ensure that month_bar handles height and width correctly
            month_bar = support.month_bar(df, height=280, width=500)
            
            sun = support.meraSunburst(df, 280)
            
            # Rendering the template with visualizations
            return render_template('analysis.html',
                                   user_name=userdata[0][1],  # Assuming userdata contains the username in second column
                                   pie=pie,
                                   bar=bar,
                                   line=line,
                                   scatter=scatter,
                                   heat=heat,
                                   month_bar=month_bar,
                                   sun=sun)
        else:
            flash("No data records to analyze.")
            return redirect('/home')
    else:  # If not logged-in
        return redirect('/')


@app.route('/home/set_goal', methods=['POST'])
def set_goal():
    if 'user_id' in session:  # Check if the user is logged in
        user_id = session['user_id']  # Get the user's session ID
        if request.method == 'POST':
            goal_name = request.form.get('goal_name')  # Retrieve goal name from form
            goal_amount = request.form.get('goal_amount')  # Retrieve goal amount from form
            try:
                # Insert the goal into the database
                query = """INSERT INTO user_goals (user_id, goal_name, goal_amount, saved_amount) 
                           VALUES ({}, '{}', {}, 0)""".format(user_id, goal_name, goal_amount)
                support.execute_query('insert', query)  # Use support.execute_query to execute the query
                flash("Goal set successfully!")
            except Exception as e:
                flash("Something went wrong: {}".format(str(e)))
                return redirect("/home")
            return redirect('/home')
    else:
        return redirect('/')

@app.route('/display_goal_data', methods=['GET'])
def display_goal_data():
    if 'user_id' in session:  # Check if the user is logged in
        # user_id = session['user_id']
        # try:
        #     conn, cur = connect_db()
            
        #     # Query to fetch the latest goal for the user
        #     query = """
        #         SELECT goal_name, goal_amount, saved_amount 
        #         FROM user_goals 
        #         WHERE user_id = ? 
        #         ORDER BY id DESC LIMIT 1
        #     """
        #     cur.execute(query, (user_id,))
        #     goal = cur.fetchone()
            
        #     # Prepare goal data as a dictionary
        #     goal_data = None
        #     if goal:
        #         goal_data = {
        #             "goal_name": goal[0],
        #             "goal_amount": goal[1],
        #             "saved_amount": goal[2],
        #         }
            
        #     # Close the connection
        #     conn.close()
            
        # except Exception as e:
        #     print(f"Error fetching goal data: {e}")
        #     goal_data = None
        
        # # Render the template and pass only the latest goal
        # return render_template('home.html', goal=goal_data)
        goals_query = """
                 SELECT goal_name, goal_amount, saved_amount 
                 FROM user_goals 
                 WHERE user_id = ? 
                 ORDER BY id DESC LIMIT 1
             """
        user_goals = support.execute_query('search', goals_query)
        return render_template('home.html', goals=user_goals)
    
    else:
        return redirect('/')
# route for stock suggestions

def get_stock_data(stock_symbol):
    """
    Fetch global stock data for a given stock symbol using yfinance.
    """
    try:
        stock = yf.Ticker(stock_symbol)
        stock_data = stock.history(period="1d")
        if not stock_data.empty:
            latest_price = stock_data['Close'].iloc[-1]
            capital = stock.info['marketCap']
            chart_url = f"https://finance.yahoo.com/chart/{stock_symbol}"
            analysis = stock.info['longBusinessSummary']
            pre_high_low = f"{stock.info['fiftyTwoWeekHigh']} / {stock.info['fiftyTwoWeekLow']}"
            pe_ratio = stock.info['trailingPE']
            return {
                "latest_price": latest_price,
                "capital": capital,
                "chart_url": chart_url,
                "analysis": analysis,
                "pre_high_low": pre_high_low,
                "pe_ratio": pe_ratio
            }
        return None
    except Exception as e:
        print(f"Error fetching data for {stock_symbol}: {e}")
        return None

@app.route('/suggest-stocks', methods=['POST'])
def suggest_stocks():
    data = request.get_json()  # Parse JSON data from the request
    risk_tolerance = data.get('risk_tolerance')
    investment_amount = float(data.get('investment_amount', 0))

    # Define stock symbols based on risk levels
    stock_symbols = {
        "low": ["TATA", "MSFT", "JNJ", "PG", "KO", "PEP", "VZ", "WMT", "PFE", "MRK"],  # Low-risk stocks
        "medium": ["TSLA", "GOOGL", "AMZN", "AAPL", "NFLX", "DIS", "SBUX", "NKE", "ADBE", "INTC"],  # Medium-risk stocks
        "high": ["NVDA", "META", "AMD", "BABA", "UBER", "LYFT", "SNAP", "TWTR", "SQ", "ZM"]  # High-risk stocks
    }

    selected_stocks = stock_symbols.get(risk_tolerance, [])
    suggestions = []

    for stock in selected_stocks:
        stock_data = get_stock_data(stock)  # Replace with your stock data fetching logic
        if stock_data:
            est_quantity = investment_amount // stock_data["latest_price"]
            suggestions.append({
                "stock": stock,
                "avg_price": stock_data["latest_price"],
                "investment_estimate": est_quantity,
                "capital": stock_data["capital"],
                "chart_url": stock_data["chart_url"],
                "analysis": stock_data["analysis"],
                "pre_high_low": stock_data["pre_high_low"],
                "pe_ratio": stock_data["pe_ratio"]
            })

    return jsonify(suggestions=suggestions)



@app.route('/profile')
def profile():
    if 'user_id' in session:  # if logged-in
        # Query for user data
        user_query = """SELECT * FROM user_login WHERE user_id = {}""".format(session['user_id'])
        userdata = support.execute_query('search', user_query)
        
        # Query for user's goals
        goals_query = """SELECT goal_id, goal_name, goal_amount, saved_amount, created_at 
                         FROM user_goals 
                         WHERE user_id = {}""".format(session['user_id'])
        user_goals = support.execute_query('search', goals_query)
        
        return render_template('profile.html', 
                               user_name=userdata[0][1], 
                               email=userdata[0][2], 
                               goals=user_goals)
    else:  # if not logged-in
        return redirect('/')



@app.route("/updateprofile", methods=['POST'])
def update_profile():
    name = request.form.get('name')
    email = request.form.get("email")
    query = """select * from user_login where user_id = {} """.format(session['user_id'])
    userdata = support.execute_query('search', query)
    query = """select * from user_login where email = "{}" """.format(email)
    email_list = support.execute_query('search', query)
    if name != userdata[0][1] and email != userdata[0][2] and len(email_list) == 0:
        query = """update user_login set username = '{}', email = '{}' where user_id = '{}'""".format(name, email,
                                                                                                      session[
                                                                                                          'user_id'])
        support.execute_query('insert', query)
        flash("Name and Email updated!!")
        return redirect('/profile')
    elif name != userdata[0][1] and email != userdata[0][2] and len(email_list) > 0:
        flash("Email already exists, try another!!")
        return redirect('/profile')
    elif name == userdata[0][1] and email != userdata[0][2] and len(email_list) == 0:
        query = """update user_login set email = '{}' where user_id = '{}'""".format(email, session['user_id'])
        support.execute_query('insert', query)
        flash("Email updated!!")
        return redirect('/profile')
    elif name == userdata[0][1] and email != userdata[0][2] and len(email_list) > 0:
        flash("Email already exists, try another!!")
        return redirect('/profile')

    elif name != userdata[0][1] and email == userdata[0][2]:
        query = """update user_login set username = '{}' where user_id = '{}'""".format(name, session['user_id'])
        support.execute_query('insert', query)
        flash("Name updated!!")
        return redirect("/profile")
    else:
        flash("No Change!!")
        return redirect("/profile")



# Load the trained Q-table
with open('q_table.pkl', 'rb') as f:
    q_table = pickle.load(f)


def calculate_user_state(user_id):
    """
    Calculate the user state based on user data.
    This is a placeholder function. You need to implement the logic based on your requirements.
    """
    # Example logic to calculate user state
    # You need to replace this with your actual logic
    user_data = support.execute_query('search', f"SELECT * FROM user_login WHERE user_id = {user_id}")
    if user_data:
        # Example: Create a state based on user data
        state = [0] * 10  # Replace with actual state calculation logic
        return state
    else:
        return [0] * 10  # Default state if user data is not found

def interpret_action(action):
    """
    Interpret the action taken by the RL agent and return recommendations.
    This is a placeholder function. You need to implement the logic based on your requirements.
    """
    # Example logic to interpret action
    # You need to replace this with your actual logic
    recommendations = []
    if action == 0:
        recommendations = [{"stock": "TATA"}, {"stock": "MSFT"}, {"stock": "JNJ"}]  # Example low-risk stocks
    elif action == 1:
        recommendations = [{"stock": "TSLA"}, {"stock": "GOOGL"}, {"stock": "AMZN"}]  # Example medium-risk stocks
    elif action == 2:
        recommendations = [{"stock": "NVDA"}, {"stock": "META"}, {"stock": "AMD"}]  # Example high-risk stocks
    elif action == 3:
        recommendations = [{"stock": "Save more money"}]
    elif action == 4:
        recommendations = [{"stock": "Spend less on non-essential items"}]
    return recommendations

@app.route('/recommendation')
def recommendation():
    if 'user_id' in session:
        user_query = """SELECT * FROM user_login WHERE user_id = {}""".format(session['user_id'])
        userdata = support.execute_query('search', user_query)
        user_id = session['user_id']
        # Example: Map user data to RL states
        state = calculate_user_state(user_id)
        agent = RLAgent(state_size=10, action_size=5)
        agent.q_table = q_table
        
        action = agent.choose_action(state)
        recommendations = interpret_action(action)
        
        # Fetch additional stock data for each recommendation
        detailed_recommendations = []
        for rec in recommendations:
            stock_data = get_stock_data(rec["stock"])
            if stock_data:
                rec.update(stock_data)
                detailed_recommendations.append(rec)
        
        return render_template('recommendation.html', recommendations=detailed_recommendations,user_id = user_id, user_name=userdata[0][1], email=userdata[0][2])
    else:
        return redirect('/')

@app.route('/logout')
def logout():
    try:
        session.pop("user_id")  # delete the user_id in session (deleting session)
        return redirect('/')
    except:  # if already logged-out but in another tab still logged-in
        return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)
