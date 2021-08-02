from flask import Flask, render_template, request, session,make_response
from flask_assets import Environment, Bundle
import mysql.connector

from flask_cors import CORS, cross_origin



from functools import wraps

from dotenv import load_dotenv
import os

from utility import *
from pprint import pprint
from math import ceil

app = Flask(__name__)

CORS(app)

# app.config['CORS_ORIGINS'] = ['http://rimawidell:5000']


load_dotenv()
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")


# db = mysql.connector.connect(host = "192.168.1.70",user="python-connector",passwd=DATABASE_PASSWORD,database = "Alsaqifa")
db = mysql.connector.connect(host = "127.0.0.1",user="root",passwd=DATABASE_PASSWORD,database = "Alsaqifa", auth_plugin='mysql_native_password',autocommit=True)


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            auth = request.authorization
            response = {}    
            

           
           
           
           
            if auth:
                cur = db.cursor(dictionary=True)
                command = 'SELECT user_id FROM authentication where username = "'+auth.username+'" AND password = "'+auth.password+'"'
                print(command)
                cur.execute(command)

                result = cur.fetchall()

                if len(result)!=1:
                    response["server message"] = "Requires authentication!"
                    return response,401  #TODO revise the response code!
                else:
                    #TODO add role restriction!
                    response["server message"] = "Hello!"
                    return f(*args, **kwargs)
                    pass
            else:
                response["server message"] = "Requires authentication!"
                return response,401  #TODO revise the response code!
            

        except Exception as e:
            response["server message"] = 'Server Error!\n"'+str(e)+'"' 
            cur.close()
            return response,500
            pass

    return decorated


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
        
        command = 'SELECT * FROM users WHERE user_id in (SELECT user_id FROM authentication where username = "'+data["username"]+'" AND password = "'+data["password"]+'")'
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




@app.route('/api/get/posts_by_tag',methods=['POST'])
@app.route('/api/get/posts_by_tag/<tag_name>',methods=['GET'])
def tag_posts(tag_name = None):
    response = {}
    
    tags = request.get_json()['tags']
    pprint(tags)

   
    try:
        cur = db.cursor(dictionary=True)
        if request.method == "GET":
            tag_name = parse_in(tag_name)
            if request.args.get('type').lower() == "brief": #FIXME add brief and stuff
                
                command = "SELECT * FROM posts WHERE post_id in (SELECT post_id FROM posts_tags WHERE tag_id in(SELECT tag_id FROM tags WHERE tag_name = \""+tag_name+"\"))"

            else:
                command = "SELECT * FROM posts WHERE post_id in (SELECT post_id FROM posts_tags WHERE tag_id in(SELECT tag_id FROM tags WHERE tag_name = \""+tag_name+"\"))"

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

        else: # it is post


            if not request.args.get('cardless'):

                response['data'] = {}
                response['data']['tags'] = []
                
                for i in tags:

                    result = []
                    tag = {}
                    tag_name = i['name']

                    command = "SELECT * FROM posts WHERE post_id in (SELECT post_id FROM posts_tags WHERE tag_id in(SELECT tag_id FROM tags WHERE tag_name = \""+tag_name+"\"))"
                    cur.execute(str(command))
                    result = cur.fetchall()
                    
                    tag['data'] = result

                    tag['name'] = i['name']
                    tag['descriptive'] = i['descriptive']

                    response['data']['tags'].append(tag)

                return response,200


            else:

                offset = 2
                page = int(request.args.get('page'))
                # print(page)
                tag_name = tags[0]['name']
                print("HELOOOOOOOOOOOOO")
                page -=1
                cur = db.cursor(dictionary=True)
            
                command = "SELECT COUNT(*) FROM posts WHERE post_id in (SELECT post_id FROM posts_tags WHERE tag_id in(SELECT tag_id FROM tags WHERE tag_name = \""+tag_name+"\"))"

                cur.execute(str(command))
                total_count = cur.fetchall()
                
                command = "SELECT * FROM posts WHERE post_id in (SELECT post_id FROM posts_tags WHERE tag_id in(SELECT tag_id FROM tags WHERE tag_name = \""+tag_name+"\")) LIMIT "+str(offset*page)+","+str(offset)+""
                cur.execute(str(command))
                result = cur.fetchall()
                cur.close()   

                if len(result) == 0:
                    return response,404    
                else:
                    
                    response["data"] = result
                    response["pages"] = {}
                    response["pages"]["current_page"] = page
                    response["pages"]["location"] = '/tags/'+str(tag_name)
                    response["pages"]["number_of_pages"] = ceil(total_count[0]['COUNT(*)']/offset)
                    # pprint(response)
                    return response,200         

        pass

    except Exception as e:
        cur.close()
        print(e)
        return response,500
        pass
    return response
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

# @auth_required
@app.route('/api/add_post',methods=['POST','GET'])
def add_post():

    #TODO Add authentication

    # resp,status = auth_required(request.authorization,"admin")

    # if status == 200:
    #     response["authorization"] = "Authorized"
    #     print("Authorized!")
    # else:
    #     print("Not Authorized!")
    #     return resp,status
    # pprint(reques)
    print("test test")
    response = {}
    print(request.headers)
    try:
        cur = db.cursor(dictionary=True)
        data = request.get_json()
        pprint(data)

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
            response["data"] = result[0]
            return response,200

        pass

    except:
        cur.close()
        return response,500
        pass


@app.route('/api/playlist/<item>',methods=['GET','POST'])
def playlist(item):
    try:
        cur = db.cursor(dictionary=True)
        response = {}
    
        if item.isdigit():
            
            command = "SELECT * FROM playlists WHERE playlist_id = "+item
            cur.execute(str(command))
            playlist = cur.fetchall()

            command = "SELECT * FROM tracks where track_id in (SELECT track_id FROM playlists_tracks WHERE playlist_id =\""+item+"\")" #FIXME add playlist info to the response!
            cur.execute(str(command))
            result = cur.fetchall()
            cur.close()
            pass

        else:

            item = parse_in(item)

            command = "SELECT * FROM playlists WHERE name = \""+item+"\""
            cur.execute(str(command))
            playlist = cur.fetchall()

            command = "SELECT * FROM tracks where track_id in (SELECT track_id FROM playlists_tracks WHERE playlist_id in (SELECT playlist_id from playlists WHERE name = \""+item+"\"))"
            cur.execute(str(command))
            result = cur.fetchall()
            cur.close()


        if len(playlist) == 0:
            response["server message"] = "Playlist not found!"

            return response,404    
        else:
            response['server message'] = None
            response['playlist_name'] = item
            response['playlist'] = playlist
            response["data"] = result
            return response,200
                
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        cur.close()
        return response,500
        pass


@app.route('/api/create/tag',methods=['POST'])
@auth_required
def add_tag():
    
    data = request.get_json()
    response = {}
    try:
        cur = db.cursor(dictionary=True)
        command = 'SELECT tag_id FROM tags WHERE tag_name = "'+data["tag_name"]+'"' 
        cur.execute(command)
        result = cur.fetchall()
        if len(result) == 0:
            command = 'INSERT INTO `tags`(`tag_name`) VALUE ("'+data["tag_name"]+'")'
            cur.execute(command)
            response["server message"] = 'Added successfully!'

            return response,201
        else:
            response["server message"] = 'Was not added!,Tag name conflict with tag_id = "'+str(result[0]["tag_id"])+'"'
            cur.close()
            return response,409
        pass
    except Exception as e:
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        cur.close()
        return response,500
        pass

@app.route('/api/add/tag_post',methods=['POST'])
@auth_required
def tag_post():
    data = request.get_json()
    response = {}

    try:
        cur = db.cursor(dictionary=True)
        command = 'SELECT * FROM posts_tags WHERE post_id = "'+str(data["post_id"])+'" AND tag_id = "'+str(data["tag_id"])+'"'
        cur.execute(command)

        result = cur.fetchall()
        print(result)
        if(len(result)!=0):
            response["server message"] = 'Was not added!,Post with post_id = "'+str(result[0]["post_id"])+'" already has tag_id = "'+str(result[0]["tag_id"])+'"'
            cur.close()
            return response,409
        
        else:
            command = 'INSERT INTO `posts_tags`(`tag_id`,`post_id`) VALUES ('+str(data["tag_id"])+','+str(data["post_id"])+')'
            cur.execute(command)
            response["server message"] = 'Added successfully!'

            return response,201
        pass
    except Exception as e:
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        cur.close()
        return response,500
        pass

@app.route("/api/get/all_playlists",methods=['POST','GET'])
def get_all_playlists():
    response = {}



    try:


        offset = 5
        if request.args.get('page'):
            page = int(request.args.get('page'))
            print(page)
            page -=1
        else:
            page = 0

        cur = db.cursor(dictionary=True)
     
        command = "SELECT COUNT(*) from playlists"
        cur.execute(str(command))
        total_count = cur.fetchall()

        cur = db.cursor(dictionary=True)
        

        command = "SELECT * from playlists LIMIT "+str(offset*page)+","+str(offset)+""
        cur.execute(str(command))
        result = cur.fetchall()
        cur.close()

        if len(result) == 0:
            return response,404    
        else:
            
            response["data"] = result
            response["pages"] = {}
            response["pages"]["current_page"] = page
            response["pages"]["location"] = '/podcasts'
            response["pages"]["number_of_pages"] = ceil(total_count[0]['COUNT(*)']/offset)
            return response,200
            
    except Exception as e :
        print("*****************",e)
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        cur.close()
        return response,500
        pass


@app.route("/api/get/all_posts",methods=['POST','GET'])
def get_all_posts():
    
    response = {}

    try:
        offset = 5
        page = int(request.args.get('page'))
        # print(page)

        page -=1
        cur = db.cursor(dictionary=True)
     
        command = "SELECT COUNT(*) from posts"
        cur.execute(str(command))
        total_count = cur.fetchall()
        
        command = "SELECT * from posts LIMIT "+str(offset*page)+","+str(offset)+""
        cur.execute(str(command))
        result = cur.fetchall()
        cur.close()

        if len(result) == 0:
            return response,404    
        else:
            
            response["data"] = result
            response["pages"] = {}
            response["pages"]["current_page"] = page
            response["pages"]["location"] = '/posts'
            response["pages"]["number_of_pages"] = ceil(total_count[0]['COUNT(*)']/offset)
            # pprint(response)
            return response,200
            
    except:
        cur.close()
        return response,500

@app.route("/api/get/user",methods=['GET'])
def get_user():
    response = {}
    try:
        if "user_id" in request.args:
            cur = db.cursor(dictionary=True)
            command = "SELECT * FROM users WHERE user_id = "+str(request.args["user_id"])
            cur.execute(command)
            result = cur.fetchall()
            cur.close()
        else:
            result = []

        if len(result)==0:
            response["server message"] = "No user found with the data provided!"
            return response,404
        else:
            response["data"] = result[0]
            response["server message"] = "User found!"
            return response,200
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        cur.close()
        return response,500
        pass


    return response

@app.route("/api/get/all_tracks",methods=['POST'])
def get_all_tracks():
    response = {}

    try:
        cur = db.cursor(dictionary=True)
        
        command = "SELECT * from tracks"
        cur.execute(str(command))
        result = cur.fetchall()
        cur.close()

        if len(result) == 0:
            return response,404    
        else:
            
            response["data"] = result
            return response,200
            
    except:
        cur.close()
        return response,500

@app.route("/api/create/playlist",methods=['POST'])
def create_playlist():
    response = {}
    print(request.headers)
    try:
        cur = db.cursor(dictionary=True)
        data = request.get_json()
        pprint(data)

        command = 'SELECT playlist_id FROM playlists WHERE name = "'+data["name"]+'"'
        cur.execute(command)
        result = cur.fetchall()
        
        if len(result)==0:
            command = 'INSERT INTO `playlists`(`name`, `visibility`) VALUES ("'+data['name']+'","'+data['visibility']+'")'
            cur.execute(str(command))
            response["server message"] = "Added successfully!"
            cur.close()
            return response,201
        else:
            response["server message"] = 'Was not added!, Name conflict with playlist_id = "'+str(result[0]["playlist_id"])+'"'
            cur.close()
            return response,409
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        cur.close()
        return response,500
        pass



@app.route("/api/add_token",methods=['POST'])
def add_token():
    response = {}

    try:
        cur = db.cursor(dictionary=True)
        data = request.get_json()
        pprint(data)

        command = 'INSERT INTO `session_tokens`(`user_id`, `token`, `creation_date`, `last_touched_date`, `expiration_date`) VALUES ("'+data["user_id"]+'","'+data["token"]+'","'+data["creation_date"]+'","'+data["last_touched_date"]+'","'+data["expiration_date"]+'")'
        print(command)
        cur.execute(str(command))
        response["server message"] = "Added successfully!"
        pprint(response)
        cur.close()
        return response,201
   
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        cur.close()
        return response,500
        pass

    pass
#--------------------------[ Posts ]--------------------------#

import time
@app.route("/api/like_post",methods=['POST','OPTIONS'])
@cross_origin()
def like_post_toggle():

    response = {}
    try:
        data = request.get_json()
        pprint(data)
        print("******************** HI")
        
        response['server message'] = "nice!"
        time.sleep(3)
        return response,200

    except Exception as e :
        print("**************** Hello")
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        return response,500
        pass


if __name__ == '__main__':
    app.run(host = '0.0.0.0',port=5001,debug=True)