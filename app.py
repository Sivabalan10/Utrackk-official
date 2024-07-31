from flask import Flask,render_template,redirect,request,jsonify,url_for
import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth
from firebase_admin import firestore

app = Flask(__name__)

cred = credentials.Certificate('utrackk-ee8ab-firebase-adminsdk-6n9l5-15d8827dcb.json')
firebase_admin.initialize_app(cred)
db = firestore.client()


# home page 
@app.route("/")
def homescreen():
    return render_template('login.html')
    
# Login call
@app.route("/login", methods =["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    
    try:
        user = auth.get_user_by_email(email)
        user_ref = db.collection('users').document(user.uid)
        user_data = user_ref.get().to_dict()
        if user_data and user_data.get('password') == password:
            utrackk_name = user_data.get('utrackk_name', '')
            role = user_data.get('role', '')
            return jsonify({'success': True, 'redirect_url': '/homepage/{}/{}/{}'.format(utrackk_name,role,user.uid)})
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'})
    
    except Exception as e:
        print("Error:", e)
        return jsonify({'success': False, 'error': 'An error occurred'})
    
# Logout call
@app.route("/logout")
def logout():
    return redirect('/')

# Sign_up page
@app.route("/sign_up")
def sign_up():
    return render_template('sign_up.html')

# Storing account
@app.route("/sign_up/account_added", methods=["GET", "POST"])
def account_added():
    if request.method == "POST":
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        try:
            user = auth.create_user(
                email=email,
                password=password
            )

            user_ref = db.collection('users').document(user.uid)
            user_ref.set({
                'email': email,
                'password': password
            })
            return jsonify({"success": True, "user_id": user.uid})
        except auth.AuthError as e:
            print(f"Authentication Error: {str(e)}")
            return jsonify({"message": "Authentication error", "details": str(e)}), 401
        except Exception as e:
            print(f"General Error: {str(e)}")
            return jsonify({"message": "Internal server error", "details": str(e)}), 500
    return render_template('sign_up.html')


# enter name page
@app.route('/enter_name/<string:user_id>')
def enter_name(user_id):
    return render_template('enter_name.html',user_id=user_id)

@app.route('/store_name/<string:user_id>', methods = ['GET','POST'])
def store_name(user_id):
    if request.method == "POST":
        data = request.get_json()
        utrackk_name = data.get("utrackk_name")
        role = data.get("role")
        try:
            user_ref = db.collection('users').document(user_id)
            user_ref.update({
                'role': role ,
                'utrackk_name' : utrackk_name
            })
            return jsonify({"success": True, "user_id": user_id, "utrackk_name": utrackk_name ,"role" : role})
        except Exception as e:
            return jsonify({"message": str(e)}), 500
    return render_template('enter_name.html',user_id =  user_id)

# homepage
@app.route('/homepage/<string:utrackk_name>/<string:role>/<string:user_id>')
def homepage(utrackk_name,role,user_id):
    return render_template('homepage.html',user_id = user_id,utrackk_name = utrackk_name,role = role)

# group_joined
@app.route("/group_joined/<string:user_id>")
def group_joined(user_id):
    return render_template('group_joined.html',user_id = user_id)

@app.route('/get-groups/<string:user_id>', methods=['GET'])
def get_groups(user_id):
    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            user_email = user_data.get('email')
        else:
            return jsonify({'success': False, 'message': 'User not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

    collections = db.collections()
    user_groups = []

    for collection in collections:
        if collection.id != 'users':
            docs = collection.stream()
            member_count = 0
            is_member = False

            for doc in docs:
                doc_data = doc.to_dict()
                member_count += 1
                if doc_data.get('email') == user_email:
                    is_member = True

            if is_member:
                user_groups.append({'name': collection.id, 'count': member_count})

    return jsonify(user_groups)

# group details
@app.route("/groups_joined/group_details/<string:grp_name>/<string:user_id>")
def group_details(grp_name,user_id):
    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            user_email = user_data.get('email')
            return render_template('group_details.html',grp_name = grp_name, user_id = user_id, user_email = user_email)
        else:
            print("user_not_found")
    except Exception as e:
        print("error in groups details rendering")
    

@app.route('/view-group-details/<string:collection_name>/<string:user_id>', methods=['GET'])
def view_group_details(collection_name,user_id):   
    collection_ref = db.collection(collection_name)
    docs = collection_ref.stream()
    
    members = []
    for doc in docs:
        doc_data = doc.to_dict()
        if doc_data.get('role') == 'staff':
            member_info = {
                'utrackk_name': doc_data.get('utrackk_name'),
                'availability': doc_data.get('availability'),
                'venue': doc_data.get('venue'),
                'email': doc_data.get('email')
            }
            members.append(member_info)

    return jsonify(members)

@app.route('/update-availability/<string:collection_name>', methods=['POST'])
def update_availability(collection_name):
    data = request.json
    email = data.get('email')

    collection_ref = db.collection(collection_name)
    docs = collection_ref.where('email', '==', email).stream()

    for doc in docs:
        doc.reference.update({
            'availability': not doc.to_dict().get('availability', False)
        })

    return jsonify({'success': True})

@app.route('/update-venue/<string:collection_name>', methods=['POST'])
def update_venue(collection_name):
    data = request.json
    email = data.get('email')
    new_venue = data.get('venue')

    collection_ref = db.collection(collection_name)
    docs = collection_ref.where('email', '==', email).stream()

    for doc in docs:
        doc.reference.update({
            'venue': new_venue
        })

    return jsonify({'success': True})

@app.route('/leave-group/<string:collection_name>', methods=['POST'])
def leave_group(collection_name):
    data = request.json
    user_email = data.get('email')

    collection_ref = db.collection(collection_name)
    docs = collection_ref.where('email', '==', user_email).stream()

    for doc in docs:
        doc.reference.delete()

    return jsonify({'success': True})




# join group
@app.route("/join_group/<string:user_id>")
def join_group(user_id):
    return render_template('join_group.html',user_id = user_id)

@app.route('/search-group', methods=['POST'])
def search_group():
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify([])

    groups_ref = db.collections()
    groups = []

    for collection in groups_ref:
        if collection.id != 'users':  
            if query.lower() in collection.id.lower():
                doc_count = len(list(collection.stream()))
                groups.append({'name': collection.id, 'count': doc_count})
    return jsonify(groups)

@app.route('/add_group/<string:user_id>', methods=['POST'])
def add_group(user_id):
    data = request.json
    group_name = data.get('groupName')
    
    if not group_name:
        return jsonify({'success': False, 'message': 'Group name is required'})

    # Fetch user details from Firestore using user_id
    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            user_email = user_data.get('email')
            user_role = user_data.get('role')
            user_name = user_data.get('utrackk_name')
        else:
            return jsonify({'success': False, 'message': 'User not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

    if not user_email or not user_role:
        return jsonify({'success': False, 'message': 'User email or role is missing'})
    try:
        group_ref = db.collection(group_name)
        query = group_ref.where('email', '==', user_email).stream()
        if any(query):
            return jsonify({'success': False, 'message': 'Email already exists in the group'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    try:
        if user_role == "staff":
            group_ref.add({
                'email': user_email,
                'role': user_role,
                'availability': False,
                'venue': "none",
                'utrackk_name': user_name
            })
        else:
            group_ref.add({
                'email': user_email,
                'role': user_role,
                'utrackk_name': user_name
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

    return jsonify({'success': True})

# join group
@app.route("/create_group/<string:user_id>")
def create_group(user_id):
    return render_template('create_group.html',user_id = user_id)

@app.route("/create_group/store/<string:user_id>" , methods = ['GET','POST'])
def store(user_id):
    data = request.json
    group_name = data.get('group_name')
    description = data.get('description')
    user_id = data.get('user_id')

    group_ref = db.collection(group_name).get()
    if group_ref:
        return jsonify({"success": False, "message": "Group name already exists"})
    
    # Fetch user data from Firestore using user_id
    user_ref = db.collection('users').document(user_id)
    user_data = user_ref.get().to_dict()

    if user_data:
        group_ref = db.collection(group_name)
        group_ref.document(user_id).set({
            'email': user_data.get('email'),
            'role': user_data.get('role'),
            'availability': False,
            'description': description,
            'group_name': group_name,
            'venue' : "none",
            'utrackk_name' : user_data.get('utrackk_name')
        })

        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "User not found"})
    

# complaint box page
@app.route("/complaint_box/<string:utrackk_name>")
def complaint_box(utrackk_name):
    return render_template('complaint_box.html',name=utrackk_name)

@app.route('/submit_complaint', methods=['POST'])
def submit_complaint():
    try:
        complaint_subject = request.json.get('subject')
        complaint_message = request.json.get('message')
        print(f"Complaint Subject: {complaint_subject}")
        print(f"Complaint Message: {complaint_message}")
        return jsonify({'success': True}), 200
    except Exception as e:
        print(e)
        return jsonify({'success': False}), 500

# mark entering 
@app.route("/enter_secured_mark")
def enter_secured_mark():
    return render_template('enter_mark.html')

#profile page
@app.route("/profile")
def profile():
    return "profile with edit icon interms of form (easy approach)"

if  __name__ == "__main__":
    # app.run(debug=True,host='0.0.0.0',port=5005)
    app.run(debug=True)
