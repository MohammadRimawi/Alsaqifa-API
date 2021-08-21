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
                print("&&&&&&&&&&&&&&&&&&&&&& ", auth.token)
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
            # cur.close()
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
        # cur.close()
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

            # if len(result) == 0:
            #     return response,404    
            # else:
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
                    tag_name = parse_in(i['name'])
                    offset = 7

                    if int(i['number_of_cards']) :
                       offset = i['number_of_cards']

                    

                    command = "SELECT res.* FROM (SELECT p.* FROM posts p LEFT JOIN posts_tags pt ON p.post_id = pt.post_id LEFT JOIN tags t ON t.tag_id = pt.tag_id WHERE t.tag_name = \""+tag_name+"\" ORDER BY p.post_id DESC LIMIT 0,"+str(offset)+") res ORDER BY res.post_id"
                    # print(command)
                    cur.execute(str(command))
                    result = cur.fetchall()
                    
                    tag['data'] = result

                    tag['name'] = i['name']
                    tag['descriptive'] = i['descriptive']

                    response['data']['tags'].append(tag)

                return response,200


            else:

                offset = 10
                page = int(request.args.get('page'))
                # print(page)
                tag_name = parse_in(tags[0]['name'])
                print("HELOOOOOOOOOOOOO")
                page -=1
                cur = db.cursor(dictionary=True)
            
                command = "SELECT COUNT(*) FROM posts WHERE post_id in (SELECT post_id FROM posts_tags WHERE tag_id in (SELECT tag_id FROM tags WHERE tag_name = \""+tag_name+"\"))"

                cur.execute(str(command))
                total_count = cur.fetchall()
                
                command = """
                SELECT

                post.*,
                GROUP_CONCAT(DISTINCT tag.tag_name) as "tags"
                From posts post 

                LEFT JOIN posts_tags pt 
                ON pt.post_id = post.post_id  

                LEFT JOIN tags tag 
                ON tag.tag_id = pt.tag_id 
                
                
                WHERE post.post_id in (SELECT pt.post_id FROM posts_tags pt WHERE pt.tag_id in(SELECT tag.tag_id FROM tags tag WHERE tag.tag_name = \""""+tag_name+"""\")) 

                GROUP BY post.post_id
            
                LIMIT """+str(offset*page)+","+str(offset)+""

                print(command)
                cur.execute(str(command))
                result = cur.fetchall()
                cur.close()   

                # if len(result) == 0:
                #     return response,404    
                # else:
                    
                response["data"] = result
                response["pages"] = {}
                response["pages"]["current_page"] = page
                response["pages"]["location"] = '/tags/'+str(tag_name)
                response["pages"]["number_of_pages"] = ceil(total_count[0]['COUNT(*)']/offset)
                    # pprint(response)
                return response,200         

        pass

    except Exception as e:
        # cur.close()
        print(str(e))
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
        # cur.close()
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
        # cur.close()
        return response,500
        pass




@app.route('/api/get/post/<post_name>')
def post(post_name):

    post_name = parse_in(post_name)
    # print(post_name)
    response = {}
    
    try:
        cur = db.cursor(dictionary=True)
        
            
        command = """
            (SELECT 
            
            post.*,
            user.name as username,
            posted_by_user.name as posted_by_name,
            GROUP_CONCAT(DISTINCT tag.tag_name) as "tags"

            
            
            FROM posts post 
            
            LEFT JOIN users user 
            ON user.user_id = post.user_id 
            
            LEFT JOIN users posted_by_user 
            ON posted_by_user.user_id = post.posted_by

            LEFT JOIN posts_tags pt 
            ON pt.post_id = post.post_id  

            LEFT JOIN tags tag 
            ON tag.tag_id = pt.tag_id 
            
            WHERE post.title = \""""+post_name+"""\" )
           
        """
        # print(command)
        cur.execute(str(command))
        result = cur.fetchall()

        command = """
            SELECT 
            
            COUNT(*)
            
            FROM posts_likes
            
            WHERE post_id = \""""+ str(result[0]['post_id']) +"""\" 
        """
        cur.execute(str(command))
        result[0]['likes_count'] = cur.fetchall()[0]['COUNT(*)']
        
        command = """
            SELECT 
            
            COUNT(*)
            
            FROM posts_comments
            
            WHERE post_id = \""""+str(result[0]['post_id'])+"""\" 
        """

        cur.execute(str(command))
        result[0]['comments_count'] = cur.fetchall()[0]['COUNT(*)']
        cur.close()

        if len(result) == 0:
            
            return response,404    
        else:
            response["post_name"] = post_name
            response["data"] = result[0]
            # pprint(response)
            return response,200

        pass

    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        # print(e)
        # cur.close()
        return response,500
        pass



@app.route('/api/playlist/<item>',methods=['GET','POST'])
def playlist(item):
    response = {}
    try:
        cur = db.cursor(dictionary=True)
    
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
        # cur.close()
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
        # cur.close()
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
        # cur.close()
        return response,500
        pass


@app.route("/api/get/all_posts",methods=['POST','GET'])
def get_all_posts():
    
    response = {}

    try:
        if request.args.get('page'):
            page = int(request.args.get('page'))-1
        else:
            page =1

        if request.args.get('offset'):
            offset = int(request.args.get('offset'))
        else:
            offset = 5

        cur = db.cursor(dictionary=True)
     
        command = "SELECT COUNT(*) from posts"
        cur.execute(str(command))
        total_count = cur.fetchall()
        
        if request.args.get('all'):
            command = "SELECT post_id,title FROM posts"
        else:
            command = """
            SELECT 
            post.* , 
            GROUP_CONCAT(DISTINCT tag.tag_name) as "tags"
            From posts post 

            LEFT JOIN posts_tags pt 
            ON pt.post_id = post.post_id  

            LEFT JOIN tags tag 
            ON tag.tag_id = pt.tag_id 
            
            GROUP BY post.post_id

            LIMIT """+str(offset*page)+""","""+str(offset)+""""""

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
            
    except Exception as e :
            response["server message"] = 'Server Error!\n"'+str(e)+'"' 
            pprint(response)
            # cur.close()
            return response,500
            pass

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
        # cur.close()
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
        # cur.close()
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
        # cur.close()
        return response,500
        pass


@app.route("/api/get/all_users",methods=['POST'])
def all_users():
    response = {}

    try:
        cur = db.cursor(dictionary=True)
        data = request.get_json()
        pprint(data)

        command=""
        print(command)
        cur.execute(str(command))

        command = "SELECT user_id,name FROM users WHERE author = 1"

        cur.execute(str(command))
        result = cur.fetchall()
        cur.close()
        response['data'] = result
        pprint(result)
        return response,201
   
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        # cur.close()
        return response,500
        pass

    pass


@app.route("/api/get/all_tags",methods=['POST','GET'])
def all_tags():
    response = {}

    try:
        cur = db.cursor(dictionary=True)


        command = "SELECT * FROM tags"

        cur.execute(str(command))
        result = cur.fetchall()
        cur.close()

        response['data'] = result
        pprint(result)
        return response,201
   
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        # cur.close()
        return response,500
        pass

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
        # cur.close()
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

@app.route("/api/add_new_post", methods=['POST'])
def add_new_post():
    response = {}
    try:
        data = request.get_json()
        cur = db.cursor(dictionary=True)
        
        command = """ INSERT INTO `posts` (`user_id`, `title`, `description`, `text`, `image_url`, `timestamp`, `posted_by`) VALUES ("""+data['user_id']+""",'"""+data['title']+"""','"""+data['text']+"""','"""+data['text']+"""','"""+data['image_url']+"""','"""+data['date']+"""',"""+data['posted_by']+""")"""
        pprint(command)
        cur.execute(str(command))
        cur.fetchall()
        post_id = cur.lastrowid

        vals = []
        for i in data['tags']:
            vals.append( "("+str(post_id)+","+str(i)+")")
        vals = ",".join(vals)
        print(vals)
        command = """ INSERT INTO `posts_tags` (`post_id`, `tag_id`) VALUES """+vals+""""""
        print(command)
        cur.execute(str(command))

        

        response["server message"] = "Added successfully!"
        pprint(response)
        cur.close()
        # response["server message"] = 'Posted!' 
        return response,200
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        # cur.close()
        return response,500
        pass


@app.route("/api/get/comments/<post_id>",methods=['POST','GET'])
def get_post_comments(post_id):
    
    response = {}

    try:
        offset = 5
        if request.args.get('page'):
            page = int(request.args.get('page'))
        else:

            page = 1
        # print(page)

        page -=1
        cur = db.cursor(dictionary=True)
        # data = request.get_json()
     
        command = "SELECT COUNT(*) from posts_comments WHERE post_id = "+str(post_id)+""
        cur.execute(str(command))
        total_count = cur.fetchall()
        #comment
        #number of comments 
        #numebr of likes on that comment

        command = """
        SELECT * FROM
        (SELECT 
        
        comments.*,
        user.name as username ,
        user.image_url as user_image_url,
        COUNT(likes.like_id) as likes_count        
        
        FROM
        comments comments 
        LEFT JOIN comments_likes likes
        on likes.comment_id = comments.comment_id

        LEFT JOIN users user 
        on user.user_id = comments.user_id
        
        WHERE 
        comments.comment_id 
        
        in (SELECT comment_id from posts_comments WHERE post_id = """+str(post_id)+""") 
        GROUP BY comments.comment_id 
        ORDER BY comments.comment_id DESC
        LIMIT """+str(offset*page)+""" , """+str(offset)+""")

        sub ORDER BY comment_id ASC

        """
        # prints(command)
        cur.execute(str(command))
        result = cur.fetchall()
        cur.close()

        # if len(result) == 0:
        #     return response,404    
        # else:
        
        response["data"] = result
        response["pages"] = {}
        response["pages"]["current_page"] = page
        response["pages"]["location"] = '/posts'
        response["pages"]["number_of_comments"] = total_count[0]['COUNT(*)']
        response["pages"]["number_of_comments_shown"] = min(total_count[0]['COUNT(*)'],(page+1)*offset)
        response["pages"]["number_of_pages"] = ceil(total_count[0]['COUNT(*)']/offset)
            # pprint(response)
        return response,200
            
    except Exception as e :
        print("**************** Hello",e)
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 

        return response,500
        pass

@app.route("/api/add_post_comment",methods=['POST'])
def add_post_comment():
    response = {}

    try:
        cur = db.cursor(dictionary=True)
        data = request.get_json()
        pprint(data)
        command = "SELECT user_id FROM session_tokens WHERE token = '"+ data['token'] +"'"
        print(command)
        cur.execute(str(command))
        user_id = cur.fetchall()[0]['user_id']
        # print(res)

        command = 'INSERT INTO `comments`(`user_id`, `text`) VALUES (\''+str(user_id)+'\',\''+data["text"]+'\')'
        # command.replace('\'',"\`")
        print(command)
        cur.execute(str(command))
        cur.fetchall()
        comment_id = cur.lastrowid
        
        command = 'INSERT INTO `posts_comments`(`comment_id`, `post_id`) VALUES ("'+str(comment_id)+'","'+str(data["post_id"])+'")'
        print(command)
        cur.execute(str(command))
        cur.fetchall()

        command = """
        SELECT 
        
        comments.*,
        user.name as username ,
        user.image_url as user_image_url,
        COUNT(likes.like_id) as likes_count        
        
        FROM
        comments comments 
        LEFT JOIN comments_likes likes
        on likes.comment_id = comments.comment_id

        LEFT JOIN users user 
        on user.user_id = comments.user_id
        
        WHERE 
        comments.comment_id = """+str(comment_id) +"""
        GROUP BY comments.comment_id 

        """

        cur.execute(str(command))
        
        response['data'] = cur.fetchall()

        response["server message"] = "Added successfully!"
      

        pprint(response)
        cur.close()
        return response,201
   
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        # cur.close()
        return response,500
        pass
    pass







#--------------------------[ Registration ]--------------------------#

#[ Update ]-----------------------#

#[ Delete ]-----------------------#


#[ Create ]-----------------------#


@app.route('/api/create/user',methods=['POST'])
def create_user():
    response = {}
    try:
        data = request.get_json()
        cur = db.cursor(dictionary=True)   

        command ="INSERT INTO `users`( `name` ) VALUES (\""+str(data['name'])+"\")"  

        cur.execute(str(command))
        cur.fetchall()
        user_id = cur.lastrowid

        response['user_id'] = user_id

        cur.close()
        return response,200
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        return response,500
        

@app.route('/api/create/authentication',methods=['POST'])
def create_authentication():
    response = {}
    try:
        data = request.get_json()
        cur = db.cursor(dictionary=True)   

        command ="INSERT INTO `authentication`(`user_id`, `username`, `password`, `email`) VALUES ("+str(data['user_id'])+",\""+str(data['username'])+"\",\""+str(data['password'])+"\",\""+str(data['email'])+"\")" 

        cur.execute(str(command))
        cur.fetchall()

        cur.close()
        response['status_code'] = 200
        return response,200
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        return response,500
        


#[ Get ]--------------------------#


#------------------------------[ Tags ]------------------------------#

#[ Create ]-----------------------#

@app.route('/api/create/tag',methods=['POST'])
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
        return response,500
        pass

#[ Get ]--------------------------#

#[ Update ]-----------------------#

@app.route('/api/update/tag',methods=['PUT'])
def update_tag():

    response = {}
    try:
        data = request.get_json()
        cur = db.cursor(dictionary=True)   

        command ="UPDATE `tags` SET `tag_id`=\""+str(data['tag_id'])+"\",`tag_name`=\""+str(data['tag_name'])+"\" WHERE tag_id = \""+str(data['tag_id'])+"\""  
        print(command)
        cur.execute(str(command))
            
        response["server message"] = 'Tag was updated!' 

        cur.close()
        return response,200
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        return response,500

#[ Delete ]-----------------------#

@app.route('/api/delete/tag',methods=['DELETE'])
def delete_tag():

    response = {}
    try:
        data = request.get_json()
        cur = db.cursor(dictionary=True)   

        command ="DELETE FROM tags WHERE tag_id = \""+str(data['tag_id'])+"\""  
        print(command)
        cur.execute(str(command))
            
        response["server message"] = 'Tag was deleted!' 

        cur.close()
        return response,200
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        return response,500
        


#-----------------------------[ Widget ]-----------------------------#

#[ Create ]-----------------------#

@app.route('/api/create/widget',methods=['POST'])
def add_widget():
    
    response = {}
    try:
        data = request.get_json()
        cur = db.cursor(dictionary=True) 

        command = "INSERT INTO `widgets`(`name`, `type`) VALUES (\""+str(data['name'])+"\",\""+str(data['type'])+"\")"
        cur.execute(str(command))
        cur.fetchall()
        widget_id = cur.lastrowid   

        if data['type'] == "slider":
           
            command = "INSERT INTO `slider_widget`(`widget_id`, `number_of_cards`, `order_by`, `tag_id`, `descriptive`, `shuffle`) VALUES (\""+str(widget_id)+"\",\""+str(data['number_of_cards'])+"\",\""+str(data['order_by'])+"\",\""+str(data['tag_id'])+"\",\""+str(data['descriptive'])+"\",\""+str(data['shuffle'])+"\")"
            cur.execute(str(command))
            return response,200

        elif data['type'] == "post":

            command = "INSERT INTO `post_widget`(`widget_id`, `post_id`) VALUES  (\""+str(widget_id)+"\",\""+str(data['post_id'])+"\")"
            cur.execute(str(command))
            return response,200

        elif data['type'] == "embeded":
            command = "INSERT INTO `embeded_widget`(`widget_id`, `code_block`) VALUES  (\""+str(widget_id)+"\",\'"+str(data['code_block'])+"\')"
            cur.execute(str(command))
            return response,200

    except Exception as e:
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        return response,500
        pass

@app.route('/api/create/page_widget',methods=['POST'])
def add_page_widget():
    
    response = {}
    try:
        data = request.get_json()
        cur = db.cursor(dictionary=True) 

        command = "INSERT INTO `page_widgets`(`widget_id`,`page`, `order_by`) VALUES (\""+str(data['widget_id'])+"\",\""+str(data['page'])+"\",\""+str(data['order_by'])+"\")"
        cur.execute(str(command))
        
        cur.close()
        return response,200

    except Exception as e:
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        return response,500
        pass

#[ Get ]--------------------------#
@app.route('/api/get/all_widgets',methods=['post'])
def all_widgets():

    response = {}
    try:
        cur = db.cursor(dictionary=True)   
        command = """ 
       
    SELECT
    w.*,
    s.number_of_cards,
    s.order_by,
    s.tag_id,
    t.tag_name,
    s.shuffle,
    s.descriptive,
    pw.post_id,
    p.title,
    ew.code_block
    FROM widgets w 

    LEFT JOIN slider_widget s ON s.widget_id = w.widget_id 
    LEFT JOIN tags t ON s.tag_id = t.tag_id

    LEFT JOIN post_widget pw ON w.widget_id = pw.widget_id 
    LEFT JOIN posts p ON p.post_id = pw.post_id

    LEFT JOIN embeded_widget ew ON w.widget_id = ew.widget_id

    LEFT JOIN 
 	page_widgets paw ON paw.widget_id = w.widget_id

 ORDER by 
 	paw.order_by

        """

        cur.execute(str(command))
        response['data'] = cur.fetchall()
        # pprint(response)
        cur.close()
        return response,200
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        return response,500


@app.route("/api/get/page_widgets", methods=['GET','POST'])
def get_page_widgets():
    response = {}

    try:
            
        data={
            "page":"home"
        }

        # data = request.get_json()
        pprint(data)

        cur = db.cursor(dictionary=True)
        if request.args.get('all'):
            command = "SELECT pw.*,w.name FROM page_widgets pw LEFT JOIN widgets w ON w.widget_id = pw.widget_id "
        else:
            command = """ 
       
    SELECT
    w.*,
    s.number_of_cards,
    s.order_by,
    s.tag_id,
    t.tag_name,
    s.shuffle,
    s.descriptive,
    pw.post_id,
    p.title,
    ew.code_block
    FROM widgets w 

    LEFT JOIN slider_widget s ON s.widget_id = w.widget_id 
    LEFT JOIN tags t ON s.tag_id = t.tag_id

    LEFT JOIN post_widget pw ON w.widget_id = pw.widget_id 
    LEFT JOIN posts p ON p.post_id = pw.post_id

    LEFT JOIN embeded_widget ew ON w.widget_id = ew.widget_id

    LEFT JOIN 
 	page_widgets paw ON paw.widget_id = w.widget_id

 WHERE 
 	paw.page = \""""+data['page']+"""\" 
 ORDER by 
 	paw.order_by

        """

        cur.execute(str(command))
        response['data'] = cur.fetchall()

        return response,200
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        # cur.close()
        return response,500
        pass
    pass
#[ Update ]-----------------------#

@app.route('/api/update/widget',methods=['PUT'])
def update_widget():

    response = {}
    try:
        data = request.get_json()
        cur = db.cursor(dictionary=True)   
        
        if data['type'] == "slider":
            command ="UPDATE `slider_widget` SET `number_of_cards`=\""+str(data['number_of_cards'])+"\",`order_by`=\""+str(data['order_by'])+"\",`tag_id`=\""+str(data['tag_id'])+"\",`descriptive`=\""+str(data['descriptive'])+"\",`shuffle`=\""+str(data['shuffle'])+"\" WHERE widget_id = \""+str(data['widget_id'])+"\""  
        elif data['type'] == "post":
            command ="UPDATE `post_widget` SET `post_id`=\""+str(data['post_id'])+"\" WHERE widget_id = \""+str(data['widget_id'])+"\""  
        elif data['type'] == "embeded":
            command ="UPDATE `embeded_widget` SET `code_block`=\'"+str(data['code_block'])+"\' WHERE widget_id = \""+str(data['widget_id'])+"\""  

        cur.execute(str(command))

        command ="UPDATE `widgets` SET `name`=\'"+str(data['name'])+"\' WHERE widget_id = \""+str(data['widget_id'])+"\""  
        cur.execute(str(command))

            
        response["server message"] = 'widget was updated!' 

        cur.close()
        return response,200
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        return response,500



@app.route('/api/update/page_widget',methods=['PUT'])
def update_page_widget():

    response = {}
    try:
        data = request.get_json()
        cur = db.cursor(dictionary=True)   

        command ="UPDATE `page_widgets` SET `page`=\""+str(data['page'])+"\",`order_by`=\""+str(data['order_by'])+"\" WHERE widget_id = \""+str(data['widget_id'])+"\""  
        print(command)
        cur.execute(str(command))
            
        response["server message"] = 'Page widget was updated!' 

        cur.close()
        return response,200
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        return response,500


#[ Delete ]-----------------------#

@app.route('/api/delete/page_widget',methods=['DELETE'])
def delete_page_widget():

    response = {}
    try:
        data = request.get_json()
        cur = db.cursor(dictionary=True)   

        command ="DELETE FROM page_widgets WHERE widget_id = \""+str(data['widget_id'])+"\""  
        print(command)
        cur.execute(str(command))
            
        response["server message"] = 'Widget was deleted!' 

        cur.close()
        return response,200
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        return response,500
        
@app.route('/api/delete/widget',methods=['DELETE'])
def delete_widget():

    response = {}
    try:
        data = request.get_json()
        cur = db.cursor(dictionary=True)   

        command ="DELETE FROM widgets WHERE widget_id = \""+str(data['widget_id'])+"\""  
        print(command)
        cur.execute(str(command))
            
        response["server message"] = 'Widget was deleted!' 

        cur.close()
        return response,200
        
    except Exception as e :
        response["server message"] = 'Server Error!\n"'+str(e)+'"' 
        pprint(response)
        return response,500
        






if __name__ == '__main__':
    app.run(host = '0.0.0.0',port=5001,debug=True)