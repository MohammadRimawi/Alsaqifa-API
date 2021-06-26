from flask import Flask, render_template, request, session,make_response
from flask_assets import Environment, Bundle
import mysql.connector

from utility import *


app = Flask(__name__)


# db = mysql.connector.connect(host = "192.168.1.70",user="python-connector",passwd="000000",database = "Alsaqifa")
db = mysql.connector.connect(host = "127.0.0.1",user="python-connector",passwd="000000",database = "Alsaqifa", auth_plugin='mysql_native_password',autocommit=True)

@app.route('/api')
def index():
    return "test"



@app.route('/api/authenticate',methods=['POST'])
def authenticate():
    data = request.get_json()
    # data = {}

    # data['username'] = "MohammadRimawi"
    # data['password'] = "000000"
    response = {}
    print(data)

    try:
        cur = db.cursor(dictionary=True)
        
        command = 'SELECT user_id FROM authentication where username = "'+data["username"]+'" AND password = "'+data["password"]+'"'
        cur.execute(str(command))
        result = cur.fetchall()
        cur.close()

        if len(result) != 1:

            #TODO Add auditing

            return make_response(response,404)    
        else:
            response["data"] = result[0]

            return make_response(response,200)
            
    except:
        cur.close()
        return make_response(response,500)





@app.route('/api/widget/tag_posts/<tag_name>')
def tag_posts(tag_name):
    tag_name = parse_in(tag_name)
    response = {}
   
    try:
        cur = db.cursor(dictionary=True)
        if request.args.get('type').lower() == "brief":
            
            command = "SELECT * FROM posts WHERE post_id in (SELECT post_id FROM posts_tags WHERE tag_id in(SELECT tag_id FROM tags WHERE tag_name = \""+tag_name+"\"))"

        else:
             command = "SELECT * FROM tags WHERE tag_name = \""+tag_name+"\""

        cur.execute(str(command))
        result = cur.fetchall()
        cur.close()

        if len(result) == 0:
            return response,404    
        else:
            response["data"] = {}
            response["data"]["type"] = request.args.get('type').lower()
            response["data"]["tag_name"] = tag_name
            response["data"]["cards"]=result
            return response,200

        pass

    except:
        cur.close()
        return response,500
        pass

    pass


@app.route('/api/post_info/<post_name>')
def post_info(post_name):

    post_name = parse_in(post_name)
    print(post_name)
    response = {}
    
    try:
        cur = db.cursor(dictionary=True)
        if request.args.get('type').lower() == "brief":
            
            command = "SELECT * FROM posts WHERE title = \""+post_name+"\""

        else:
            #FIXME
             command = "SELECT * FROM posts WHERE title = \""+post_name+"\""

        cur.execute(str(command))
        result = cur.fetchall()
        cur.close()
        if len(result) == 0:
            return response,404    
        else:
        #TODO just make it take the required data only
            response["post_name"] = post_name
            response["data"] = result
            return response,200

        pass

    except:
        cur.close()
        return response,500
        pass

@app.route('/api/add_post',methods=['POST'])
def add_post():
    data = request.get_json()
    response = {}

    try:
        cur = db.cursor(dictionary=True)
        command = 'SELECT post_id FROM posts WHERE title = "'+data["title"]+'"'
        cur.execute(command)
        result = cur.fetchall()
        
        if len(result)==0:
            command = 'INSERT INTO `posts`(`user_id`, `title`, `description`, `text`, `image_url`, `posted_by`) VALUES ("'+str(data["user_id"])+'","'+data["title"]+'","'+data["description"]+'","'+data["text"]+'","'+data["image_url"]+'","'+str(data["posted_by"])+'")'
            cur.execute(str(command))
            response["server message"] = "Added successfully!"
            cur.close()
            return response,201
        else:
            response["server message"] = 'Was not added!,Title conflict with post_id = "'+str(result[0]["post_id"])+'"'
            cur.close()
            return response,409

    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        cur.close()
        return response,500
        pass




@app.route('/api/post/<post_name>')
def post(post_name):

    post_name = parse_in(post_name)
    print(post_name)
    response = {}
    
    try:
        cur = db.cursor(dictionary=True)
            
        command = "SELECT * FROM posts WHERE title = \""+post_name+"\""
            
        cur.execute(str(command))
        result = cur.fetchall()
        cur.close()

        if len(result) == 0:
            return response,404    
        else:
            response["post_name"] = post_name
            response["data"] = result
            return response,200

        pass

    except:
        cur.close()
        return response,500
        pass

   



@app.route('/api/playlist/<playlist_name>',methods=['GET','POST'])
def playlist(playlist_name):
  
    playlist_name = parse_in(playlist_name)
    response = {}

    try:
        cur = db.cursor(dictionary=True)
        
        command = "SELECT * FROM tracks where track_id in (SELECT track_id FROM playlists_tracks WHERE playlist_id in (SELECT playlist_id from playlists WHERE name = \""+playlist_name+"\"))"
        cur.execute(str(command))
        result = cur.fetchall()
        cur.close()

        if len(result) == 0:
            return response,404    
        else:
            response["playlist_name"] = playlist_name
            response["data"] = result
            return response,200
            
    except:
        cur.close()
        return response,500






if __name__ == '__main__':
    app.run(host = '0.0.0.0',port=5001,debug=True)