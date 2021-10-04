from flask import Flask, render_template, request, session,make_response, g
import mysql.connector
from sqlalchemy import create_engine
from jsql import sql
from functools import wraps
from dotenv import load_dotenv
import os
from utility import *
from pprint import pprint
from math import ceil

app = Flask(__name__)


load_dotenv()

DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_HOST = os.getenv("DATABASE_HOST")

engine = create_engine(f'mysql+mysqlconnector://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}/{DATABASE_NAME}')



#-----------------------------[ Utility ]----------------------------#

@app.before_request
def before_request_func():
    g.conn = engine.connect()
    g.transaction = g.conn.begin()
  
    g.data = {}
    if request.data:
        g.data = request.get_json()
    
    
    g.user_id = -1
    if 'token' in g.data:
        g.user_id = sql(g.conn,
        '''
            SELECT 
                user_id
            FROM 
                session_tokens 
            WHERE token = :token
        '''
        ,token=g.data['token']).scalar()

    print("request by: ",g.user_id)

@app.after_request
def after_request_func(response):
    
    if response.status_code >= 400 :
        g.transaction.rollback()
        res = response.get_json()
        if 'server message' in res:
            pprint(res['server message'])
        if 'response' in res and 'error' in res['response']:
            pprint(res['response']['error'])
    else:
        g.transaction.commit()
    g.conn.close()
    return response


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            auth = request.authorization
            
            response = {}    
           
            if auth:
                

                print("&&&&&&&&&&&&&&&&&&&&&& ", auth.token)
                command = 'SELECT user_id FROM authentication where username = "'+auth.username+'" AND password = "'+auth.password+'"'
                print(command)


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
            return response,500
            pass

    return decorated




@app.route('/api')
def index():
    print('hello')
    name = "hello"
    res = sql(g.conn,'INSERT INTO `users` ( `name` ) VALUE (:name)', name = name).lastrowid
    print(res)
    return str(res)



@app.route('/api/authenticate',methods=['POST'])
def authenticate():
    data = request.get_json()
    # data = {}

    # data['username'] = "MohammadRimawi"
    # data['password'] = "000000"
    response = {}
    print(data,"**********")

    try:
        
        # command = 'SELECT * FROM users u LEFT JOIN authentication a on a.user_id = u.user_id where a.username = "'+data["username"]+'" AND a.password = "'+data["password"]+'"'
        result = sql(g.conn,'''
            SELECT 
                * 
            FROM 
                users u 
            LEFT JOIN 
                authentication a 
            ON 
                a.user_id = u.user_id 
            WHERE 
                a.username = :username 
            AND 
                a.password = :password
        ''',**g.data).dict()


        if not result:

            #TODO Add auditing

            return make_response(response,404)    
        else:
            print(result)
            response["data"] = result

            return make_response(response,200)
            
    except Exception as e:
        print(e)
        return response,500
        pass
    return response
    pass






######################################################################
#--------------------------[ Registration ]--------------------------#
######################################################################

###################################
#[ Create ]-----------------------#
###################################

# Description   :   puts user into users table with only name attribute 
# End-point     :   /api/create/user
# Methods       :   [ POST ]
# Takes         :   name attributes
# Returns       :   user_id

@app.route('/api/create/user',methods=['POST'])
def create_user():
    response = {}
    response['data'] = {}
    response['response'] = {}
    try:
        data = request.get_json()

        user_id = sql(g.conn,'INSERT INTO `users` ( `name` ) VALUE (:name)', name = data['name']).lastrowid
        response['data']['user_id'] = user_id

        
        response['response']["message"] = f'user with name: {data["name"]} was added!' 
        response['response']["status"] = 200
        
    except Exception as e :
        response['response']["error"] = 'Server Error!\n"'+str(e)+'"' 
        response['response']["status"] = 500
    finally:
        return response,response['response']["status"]




# Description   :   puts authentication data into authentication table
# End-point     :   /api/create/authentication 
# Methods       :   [ POST ]
# Takes         :   user_id,username,password and email
# Returns       :   nothing

@app.route('/api/create/authentication',methods=['POST'])
def create_authentication():
    response = {}
    response['data'] = {}
    response['response'] = {}
    try:
        data = request.get_json()
        sql(g.conn,'''
        
        INSERT INTO 
            `authentication`(`user_id`, `username`, `password`, `email`)
        VALUE 
            (:user_id, :username, :password ,:email)

        ''',**data)

        response['response']["message"] = f'user authentication for user_id {data["user_id"]} was added!' 
        response['response']["status"] = 200
        
    except Exception as e :
        response['response']["error"] = 'Server Error!\n"'+str(e)+'"' 
        response['response']["status"] = 500
    finally:
        return response,response['response']["status"]




# Description   :   puts session token into session_tokens table
# End-point     :   /api/add/token
# Methods       :   [ POST ]
# Takes         :   user_id,token,creation_date,last_touched_date, and expiration_date
# Returns       :   Nothing.

@app.route("/api/add/token",methods=['POST'])
def add_token():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:

        sql(g.conn,
        '''
            INSERT INTO 
                `session_tokens` (`user_id`, `token`, `creation_date`, `last_touched_date`, `expiration_date`) 
            VALUES
                ( :user_id , :token , :creation_date , :last_touched_date , :expiration_date )
        '''
        ,**g.data)

        response['response']["status"] = 200
        
    except Exception as e :
        response['response']["error"] = 'Server Error!\n"'+str(e)+'"' 
        response['response']["status"] = 500
    finally:
        return response,response['response']["status"]




###################################
#[ Get ]--------------------------#
###################################

# Description   :   Gets user data from users table
# End-point     :   /api/get/user 
# Methods       :   [ POST ]
# Takes         :   user_id
# Returns       :   dict with user_id,name,image_url,title and roles if found and empty dict otherwise

@app.route("/api/get/user",methods=['POST'])
def get_user():
    response = {}
    response['data'] = {}
    response['response'] = {}
    try:
        data = request.get_json()
      
        result = sql(g.conn,'''
            SELECT *
            FROM
                `users`
            WHERE
                user_id = :user_id
        ''',user_id = data['user_id']).dict()

        
        if not result:
            response['response']["message"] = "No user found with the data provided!"
            response['response']["status"] = 404
        else:
            response["data"] = result
            response['response']["message"] = "User found!"
            response['response']["status"] = 200

    except Exception as err :
        response['response']["error"] = 'Server Error!\n"'+str(err)+'"' 
        response['response']["status"] = 500

    finally:
        return response,response['response']["status"]
        



###################################
#[ Update ]-----------------------#
###################################

###################################
#[ Delete ]-----------------------#
###################################






######################################################################
#-----------------------------[ Widget ]-----------------------------#
######################################################################

###################################
#[ Create ]-----------------------#
###################################

# Description   :   Creates widget of type : [ slider , post , embedded ]
# End-point     :   /api/create/widget
# Methods       :   [ POST ]
# Takes         :   type and for: 
#                               | slider    [ `number_of_cards`, `order_by`, `tag_id`, `descriptive`, `shuffle` ]
#                               | post      [ `post_id` ]
#                               | embedded  [ `code_block` ]
# Returns       :   nothing

@app.route('/api/create/widget',methods=['POST'])
def add_widget():
    
    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = request.get_json() 

        widget_id = sql(g.conn,
        '''
            INSERT INTO 
                `widgets`(`name`, `type`) 
            VALUES
            ( :name , :type )
        '''
        ,**data).lastrowid
        
        if data['type'] == "slider":
           
            sql(g.conn,
            '''
                INSERT INTO 
                    `slider_widget`(`widget_id`, `number_of_cards`, `order_by`, `tag_id`, `descriptive`, `shuffle`) 
                VALUES
                (:widget_id, :number_of_cards, :order_by, :tag_id, :descriptive, :shuffle)
            '''
            ,**data,widget_id = widget_id)

            response['response']['status'] = 201

        elif data['type'] == "post":
            
            sql(g.conn,
            '''
                INSERT INTO 
                    `post_widget`(`widget_id`, `post_id`)
                VALUES
                (:widget_id, :post_id)
            '''

            ,**data,widget_id = widget_id)
            response['response']['status'] = 201

        elif data['type'] == "embeded":
            
            sql(g.conn,
            '''
                INSERT INTO 
                    `embeded_widget`(`widget_id`, `code_block`)
                VALUES
                (:widget_id, :code_block)
            '''
            ,**data,widget_id = widget_id)

            response['response']['status'] = 201
  
        else:
            response['response']['status'] = 404
            

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500

    finally:
        return response,response['response']['status']
        



# Description   :   Assigns a widget to a page
# End-point     :   /api/create/page_widget
# Methods       :   [ POST ]
# Takes         :   widget_id, page, and order_by for which it is ordered in that page.
# Returns       :   nothing

@app.route('/api/create/page_widget',methods=['POST'])
def add_page_widget():
    
    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = request.get_json()
        #TODO make { widget_id,page } composite primary key  
        sql(g.conn,
            '''
                INSERT INTO 
                    `page_widgets`(`widget_id`,`page`, `order_by`)
                VALUES
                ( :widget_id , :page , :order_by )
            '''
            ,**data)
        response['response']['status'] = 201

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




###################################
#[ Get ]--------------------------#
###################################

# Description   :   Gets all widgets and thier readable information in a dict
# End-point     :   /api/get/all_widgets
# Methods       :   [ POST ]
# Takes         :   Nothing.
# Returns       :   widget_id ,type,   
#                                    | slider    [ `number_of_cards`, `order_by`, `tag_id`, `descriptive`, `shuffle` ] 
#                                    | post      [ `post_id` ]
#                                    | embedded  [ `code_block` ]
#                   **Only values for the chosen type will be populated and None in the other types

@app.route('/api/get/all_widgets',methods=['post'])
def all_widgets():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:

        response['data'] = sql(g.conn,
            '''
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

                LEFT JOIN 
                    slider_widget s 
                ON 
                    s.widget_id = w.widget_id 


                LEFT JOIN 
                    tags t 
                ON 
                    s.tag_id = t.tag_id

                LEFT JOIN 
                    post_widget pw 
                ON 
                    w.widget_id = pw.widget_id 

                LEFT JOIN 
                    posts p 
                ON 
                    p.post_id = pw.post_id

                LEFT JOIN 
                    embeded_widget ew 
                ON 
                    w.widget_id = ew.widget_id

                LEFT JOIN 
                    page_widgets paw 
                ON 
                    paw.widget_id = w.widget_id

                ORDER by 
 	                paw.order_by
            '''
            ).dicts()

        response['response']['status'] = 200
        
    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




# Description   :   Gets all widgets that are assigned to a page and thier readable information in a dict
# End-point     :   /api/get/page_widgets
# Methods       :   [ POST ]
# Takes         :   page.
# Returns       :   widget_id ,type,   
#                                    | slider    [ `number_of_cards`, `order_by`, `tag_id`, `descriptive`, `shuffle` ] 
#                                    | post      [ `post_id` ]
#                                    | embedded  [ `code_block` ]
#                   **Only values for the chosen type will be populated and None in the other types

@app.route("/api/get/page_widgets", methods=['POST'])
def get_page_widgets():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
            
        data = request.get_json()

        response['data'] = sql(g.conn,
        '''
       
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
            FROM 
                widgets w 

            LEFT JOIN 
                slider_widget s 
            ON 
            s.widget_id = w.widget_id 
            
            LEFT JOIN 
                tags t 
            ON 
            s.tag_id = t.tag_id

            LEFT JOIN 
                post_widget pw 
            ON 
            w.widget_id = pw.widget_id 
            
            LEFT JOIN 
                posts p 
            ON 
            p.post_id = pw.post_id

            LEFT JOIN 
                embeded_widget ew 
            ON 
            w.widget_id = ew.widget_id

            LEFT JOIN 
                page_widgets paw 
            ON 
            paw.widget_id = w.widget_id

            WHERE 
                paw.page = :page 
            ORDER by 
                paw.order_by

        ''',**data).dicts()

        response['response']['status'] = 200
    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']





# Description   :   Gets all widgets that are assigned to a page and thier readable information in a dict
# End-point     :   /api/get/all_page_widgets
# Methods       :   [ POST ]
# Takes         :   Nothing.
# Returns       :   widget_id, name ,page, order_by

@app.route("/api/get/all_page_widgets", methods=['POST'])
def get_all_page_widgets():
    
    response = {}
    response['data'] = {}
    response['response'] = {}

    try:  
        response['data'] = sql(g.conn,
        '''
            SELECT 
                pw.*,w.name 
            FROM 
                page_widgets pw 
            
            LEFT JOIN 
            widgets w 
            ON 
            w.widget_id = pw.widget_id 
            ''').dicts()
       
        response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




###################################
#[ Update ]-----------------------#
###################################

# Description   :   Update widgets 
# End-point     :   /api/update/widget
# Methods       :   [ PUT ]
# Takes         :   widget_id ,type,   
#                                    | slider    [ `number_of_cards`, `order_by`, `tag_id`, `descriptive`, `shuffle` ] 
#                                    | post      [ `post_id` ]
#                                    | embedded  [ `code_block` ]
# Returns       :   response message.

@app.route('/api/update/widget',methods=['PUT'])
def update_widget():
    
    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = request.get_json()
        
        if data['type'] == "slider":
            sql(g.conn,
            '''
                UPDATE 
                    `slider_widget` 
                SET 
                    `number_of_cards`= :number_of_cards,
                    `order_by`= :order_by,
                    `tag_id`= :tag_id,
                    `descriptive`= :descriptive,
                    `shuffle`= :shuffle
                WHERE 
                    `widget_id` = :widget_id 
            '''
            ,**data)
        elif data['type'] == "post":
            sql(g.conn,
            '''
                UPDATE 
                    `post_widget` 
                SET 
                    `post_id`= :post_id
                 WHERE 
                    `widget_id` = :widget_id 
            '''
            ,**data)
        elif data['type'] == "embeded":
            sql(g.conn,
            '''
                UPDATE 
                    `embeded_widget` 
                SET 
                    `code_block`= :code_block
                 WHERE 
                    `widget_id` = :widget_id 
            '''
            ,**data)
        
        
        sql(g.conn,
        '''
            UPDATE 
                `widgets` 
            SET 
                `name`= :name
            WHERE 
                    `widget_id` = :widget_id  
        '''
        ,**data)    
            
        response['response']['message'] = 'widget was updated!' 
        response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




# Description   :   Update page widgets 
# End-point     :   /api/update/page_widget
# Methods       :   [ PUT ]
# Takes         :   widget_id ,page , order_by in which it will be ordered in that page.
# Returns       :   response message.

@app.route('/api/update/page_widget',methods=['PUT'])
def update_page_widget():
    
    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = request.get_json()
        
        sql(g.conn,
        '''
            UPDATE 
                `page_widgets` 
            SET 
                `page` = :page,
                `order_by` = :order_by
                WHERE 
                `widget_id` = :widget_id 
        '''
        ,**data)

        response['response']['message'] = 'Page widget was updated!'
        response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']


###################################
#[ Delete ]-----------------------#
###################################

# Description   :   Deletes page widgets 
# End-point     :   /api/delete/page_widget
# Methods       :   [ DELETE ]
# Takes         :   widget_id.
# Returns       :   response message.

@app.route('/api/delete/page_widget',methods=['DELETE'])
def delete_page_widget():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = request.get_json()

        sql(g.conn,
        '''
            DELETE 
            FROM 
        
            `page_widgets`

            WHERE 
                `widget_id` = :widget_id 
        '''
        ,**data)

        response['response']['message'] = 'Page widget was deleted!' 
        response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




# Description   :   Deletes widgets 
# End-point     :   /api/delete/widget
# Methods       :   [ DELETE ]
# Takes         :   widget_id.
# Returns       :   response message.

@app.route('/api/delete/widget',methods=['DELETE'])
def delete_widget():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = request.get_json()

        sql(g.conn,
        '''
            DELETE 
            FROM 
        
            `widgets`

            WHERE 
                `widget_id` = :widget_id 
        '''
        ,**data)

        response['response']['message'] = 'Widget was deleted!' 
        response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']





######################################################################
#------------------------------[ User ]------------------------------#
######################################################################

###################################
#[ Create ]-----------------------#
###################################

###################################
#[ Get ]--------------------------#
###################################

# Description   :   Returns all users with the specified role 
# End-point     :   /api/get/all_users
# Methods       :   [ POST ]
# Takes         :   role.
# Returns       :   dict with user info.

@app.route("/api/get/all_users",methods=['POST'])
def all_users():
    
    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
 
        data = request.get_json()

        if data['role'] == 'author':
            response['data'] = sql(g.conn,
            '''
                SELECT 
                    user_id,
                    name
                FROM
                    `users`
                WHERE
                    author = 1
            '''
            ).dicts()
            response['response']['status'] = 200
        else:
            response['response']['status'] = 406

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']


###################################
#[ Update ]-----------------------#
###################################

###################################
#[ Delete ]-----------------------#
###################################




######################################################################
#-----------------------------[ Posts ]------------------------------#
######################################################################

###################################
#[ Create ]-----------------------#
###################################

# Description   :   Creates new post.
# End-point     :   /api/create/post
# Methods       :   [ POST ]
# Takes         :   [ user_id, title, description, text, image_url, date, posted_by ]
# Returns       :   Nothing.

@app.route("/api/create/post", methods=['POST'])
def add_new_post():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = request.get_json()
        pprint(data)
        post_id = sql(g.conn,
        '''
            INSERT INTO 
                `posts` (`user_id`, `title`, `description`, `text`, `image_url`, `timestamp`, `posted_by`) 
            VALUES
                ( :user_id , :title , :description , :text , :image_url , :date , :posted_by )  
        '''
        ,**data).lastrowid

                
        if len(data['tags'])!=0:
            vals = []
            for i in data['tags']:
                vals.append((int(post_id),int(i)))
        
            #TODO figure out multi-row insert with validation
            res = sql(g.conn, 
            '''
            INSERT INTO    
                `posts_tags` (`post_id`, `tag_id`) 
            VALUES 
                {% for val in vals %} ({{val[0]}},{{val[1]}}) {% if not loop.last %}, {% endif %}{% endfor %}
            '''
            , post_id = post_id,vals=(vals)) 
        

        response['response']['message'] = "Added successfully!"
        response['response']['status'] = 200
        
    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']





# Description   :   Creates new comment on chosen post.
# End-point     :   /api/create/comment
# Methods       :   [ POST ]
# Takes         :   [ token, text, post_id ]
# Returns       :   comment.

@app.route("/api/create/comment",methods=['POST'])
def add_post_comment():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:

        comment_id = sql(g.conn,
        '''
            INSERT INTO
                `comments`(`user_id`, `text`) 
            VALUES
                ( :user_id , :text ) 
        '''
        ,user_id = g.user_id,**g.data).lastrowid


        sql(g.conn,
        '''
            INSERT INTO 
                `posts_comments`(`comment_id`, `post_id`) 
            VALUES 
                ( :comment_id, :post_id) 
        '''
        ,comment_id = comment_id ,**g.data)

        response['data'] = sql(g.conn,
        '''
            SELECT 
            
                comments.*,
                user.name as username ,
                user.image_url as user_image_url,
                COUNT(likes.like_id) as likes_count        
            
            FROM
                comments comments 
            LEFT JOIN 
                comments_likes likes
            on 
                likes.comment_id = comments.comment_id

            LEFT JOIN 
                users user 
            on 
                user.user_id = comments.user_id
            
            WHERE 
                comments.comment_id = :comment_id
            GROUP BY 
                comments.comment_id
        ''' 
        ,comment_id = comment_id ).dicts()


        response['response']['message'] = "Added successfully!"
        response['response']['status'] = 200

        pprint(response)
        
    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']



###################################
#[ Toggle ]-----------------------#
###################################

# Description   :   toggles likes for posts.
# End-point     :   /api/toggle/like_post
# Methods       :   [ POST ]
# Takes         :   user_id and post_id.
# Returns       :   Nothing.

@app.route("/api/toggle/like_post",methods=['POST'])
def like_post_toggle():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = request.get_json()
        pprint(data)

        result = sql(g.conn,
        '''
            SELECT 
                l.like_id 
            FROM 
                `likes` l 
            LEFT JOIN 
                `posts_likes` pl 
            ON
                l.like_id = pl.like_id 
            WHERE 
                l.user_id = :user_id AND pl.post_id = :post_id
        '''
        ,**data).scalar()

        if not result:
            data['like_id']  = sql(g.conn,'''
                INSERT INTO 
                    `likes`(`user_id`) 
                VALUES 
                    ( :user_id )
            ''',**data).lastrowid


            sql(g.conn,'''
                INSERT INTO 
                    `posts_likes`(`like_id`,`post_id`) 
                VALUES 
                    ( :like_id , :post_id )
            ''',**data)
                
            response['response']['message'] = "Post liked!"
            response['liked'] = True
        

        
        else:

            sql(g.conn,
            '''
                DELETE FROM `likes` WHERE like_id = :liked_id
            '''
            ,liked_id = result)          


            response['response']['message'] = "Post unliked!"
            response['liked'] = False

            
        response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




# Description   :   toggles likes for comments.
# End-point     :   /api/toggle/like_comment
# Methods       :   [ POST ]
# Takes         :   user_id and comment_id.
# Returns       :   Nothing.

@app.route("/api/toggle/like_comment",methods=['POST'])
def like_comment_toggle():
    
    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = request.get_json()
        pprint(data)

        result = sql(g.conn,
        '''
            SELECT 
                l.like_id 
            FROM 
                `likes` l 
            LEFT JOIN 
                `comments_likes` cl 
            ON 
                l.like_id = cl.like_id 
            WHERE 
                l.user_id = :user_id AND  cl.comment_id = :comment_id
        '''
        ,**data).scalar()


        if not result:
            
            data['like_id'] = sql(g.conn,
            '''
                INSERT INTO 
                    `likes`(`user_id`) 
                VALUES 
                    ( :user_id )
            '''
            ,**data).lastrowid


            sql(g.conn,
            '''
                INSERT INTO 
                    `comments_likes` (`like_id`, `comment_id`) 
                VALUES 
                    ( :like_id , :comment_id )
            '''
            ,**data)
                        
            response['response']['message'] = "Comment liked!"
            response['liked'] = True

        else:
            sql(g.conn,
            '''
                DELETE FROM `likes` WHERE like_id = :like_id
            '''
            ,like_id = result)
            response['response']['message'] = "Comment unliked!"
            response['liked'] = False
    
        response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']


###################################
#[ Get ]--------------------------#
###################################

# Description   :   Returns dict of cards for slider or for pages 
# End-point     :   /api/get/posts_by_tag
# Methods       :   [ POST ]
# Takes         :   page, offset, tag_name, and if slider
# Returns       :   dict with posts info.

@app.route('/api/get/posts_by_tag',methods=['POST'])
def tag_posts():
    
    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        tags = request.get_json()['tags']

        if not request.args.get('slider'):

            response['data'] = {}
            response['data']['tags'] = []
            
            for i in tags:

                result = []
                tag = {}
                tag_name = parse_in(i['name'])
                offset = 7

                if int(i['number_of_cards']) :
                    offset = int(i['number_of_cards'])
                    

                tag['data'] = sql(g.conn,
                '''
                    SELECT 
                        res.* 
                        
                    FROM 
                        (
                            SELECT 
                                p.* 
                            FROM 
                                posts p 
                            
                            LEFT JOIN 
                                posts_tags pt 
                            ON 
                                p.post_id = pt.post_id 
                            
                            LEFT JOIN 
                                tags t 
                            ON 
                                t.tag_id = pt.tag_id
                            WHERE 
                                t.tag_name = :tag_name
                            ORDER BY 
                                p.post_id DESC 
                            
                            LIMIT 0,:offset
                            
                        ) res 
                        ORDER BY 
                            res.post_id
                '''
                ,tag_name = tag_name,offset = offset).dicts()
                
                tag['name'] = i['name']
                tag['descriptive'] = i['descriptive']

                response['data']['tags'].append(tag)
            
            response['response']['status'] = 200



        else:

            if request.args.get('page'):
                page = int(request.args.get('page')) - 1
            else:
                page = 0

            offset = 10
            tag_name = parse_in(tags[0]['name'])

        
            total_count = sql(g.conn,
            '''
                SELECT 
                    COUNT(*) 
                FROM 
                    posts p 

                LEFT JOIN 
                    posts_tags pt
                ON
                    p.post_id = pt.post_id

                LEFT JOIN
                    tags t
                ON
                    t.tag_id = pt.tag_id

                WHERE 
                    t.tag_name = :tag_name
            '''
            ,tag_name=tag_name).scalar()

      
            
            response['data'] = sql(g.conn,
            '''
                SELECT 
                    res.* 
                FROM
                    (
                        SELECT 
                            post.*,
                            GROUP_CONCAT(DISTINCT tag.tag_name) as "tags"

                        FROM 
                            posts post 

                        LEFT JOIN 
                            posts_tags post_tag 
                        ON
                            post_tag.post_id = post.post_id
                        LEFT JOIN 
                            tags tag 
                        ON 
                            tag.tag_id = post_tag.tag_id

                        GROUP by 
                            post.post_id
                    ) res

                WHERE
                    res.tags like :tag_name

                ORDER BY 
                    res.post_id
                LIMIT :page, :offset

            ''',tag_name = "%"+tag_name+"%",page = offset*page, offset=offset).dicts()
 
            response["pages"] = {}
            response["pages"]["current_page"] = page
            response["pages"]["location"] = '/tags/'+str(tag_name)
            response["pages"]["number_of_pages"] = ceil(total_count/offset)

            response['response']['status'] = 200


    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




# Description   :   Returns dict of comments in a post and if the user liked the comment or not.
# End-point     :   /api/get/comments
# Methods       :   [ POST ]
# Takes         :   page, offset, post_id, and user_id
# Returns       :   dict with comments info.

@app.route("/api/get/comments",methods=['POST'])
def get_post_comments():


    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        if request.data:
            data = request.get_json()
        else:
            data={}
            data['user_id'] = -1

        offset = 5
        if request.args.get('page'):
            page = int(request.args.get('page')) - 1
        else:
            page = 0

        total_count = sql(g.conn,
            '''
                SELECT 
                    COUNT(*) 
                FROM   
                    posts_comments 
                WHERE 
                    post_id = :post_id
            '''
        ,**data).scalar()
        
        response["data"] = sql(g.conn,
        '''
            SELECT 
                * 
            FROM
                (
                    SELECT 
                
                        comments.*,
                        user.name as username ,
                        user.image_url as user_image_url,
                        COUNT(likes.like_id) as likes_count        
                
                    FROM
                        comments comments 
                    
                    LEFT JOIN 
                        comments_likes likes
                    ON 
                        likes.comment_id = comments.comment_id

                    LEFT JOIN 
                        users user 
                    ON 
                        user.user_id = comments.user_id
                    
                    WHERE 
                        comments.comment_id 
                    IN 
                        (
                            SELECT 
                                comment_id 
                            FROM 
                                posts_comments 
                            WHERE 
                                post_id = :post_id
                        ) 
                    
                    GROUP BY 
                        comments.comment_id 
                    ORDER BY 
                        comments.comment_id DESC

                    LIMIT :page , :offset
                ) sub 

            ORDER BY 
                comment_id ASC
        '''
        ,**data,page = offset*page,offset = offset).dicts()


        
        liked_list = sql(g.conn,
        '''
            SELECT 
                pc.comment_id,
            CASE
                WHEN l.user_id = :user_id THEN "1"
                ELSE "0"
            END AS "liked"
            FROM 
                posts_comments pc 
            
            LEFT JOIN 
                comments_likes cl 
            ON 
                cl.comment_id = pc.comment_id 
            
            LEFT JOIN 
                likes l 
            ON 
                cl.like_id = l.like_id

            WHERE pc.post_id = :post_id
        '''
        ,**data,page = offset*page,offset = offset).dicts()
       

        for i in range(len(response["data"])):
            for j in range(len(liked_list)):
                if response["data"][i]['comment_id'] == liked_list[j]['comment_id']:
                    response["data"][i]['liked'] = liked_list[j]['liked'] 
                    
        response["pages"] = {}
        response["pages"]["current_page"] = page
        response["pages"]["location"] = '/posts'
        response["pages"]["number_of_comments"] = total_count
        response["pages"]["number_of_comments_shown"] = min(total_count,(page+1)*offset)
        response["pages"]["number_of_pages"] = ceil(total_count/offset)
       
        response['response']['status'] = 200
    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




# Description   :   Returns the comment text.
# End-point     :   /api/get/comment
# Methods       :   [ POST ]
# Takes         :   comment_id
# Returns       :   dict with comment text and comment_id.

@app.route("/api/get/comment",methods=['POST'])
def get_comment():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = request.get_json()
        response['data'] = sql(g.conn, 
            '''
                SELECT 
                    comment_id,
                    text
                FROM 
                    `comments` 
                WHERE 
                    comment_id = :comment_id
            '''
        ,**data).dict()
        if response['data']:
            response['response']['status'] = 200
        else:
            response['response']['status'] = 404

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




# Description   :   Returns all posts
# End-point     :   /api/get/all_posts
# Methods       :   [ POST ]
# Takes         :   page,offset and boolean all.
# Returns       :   dict with post info.

@app.route("/api/get/all_posts",methods=['POST','GET'])
def get_all_posts():
    
    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        if request.args.get('page'):
            page = int(request.args.get('page'))-1
        else:
            page = 0

        if request.args.get('offset'):
            offset = int(request.args.get('offset'))
        else:
            offset = 5


        total_count = sql(g.conn,
        '''
            SELECT 
                COUNT(*)
            FROM
                posts
        '''
        ).scalar()
        
        if request.args.get('all'):
            # response["data"] = "SELECT post_id,title FROM posts"

            response['data'] = sql(g.conn,
            '''
                SELECT 
                    post_id,
                    title
                FROM
                    posts
                
            '''
            ).dicts()
        
        else:
            response['data'] = sql(g.conn,
            '''
                SELECT 
                    post.* , 
                    GROUP_CONCAT(DISTINCT tag.tag_name) as "tags"
                FROM 
                    posts post 

                LEFT JOIN 
                    posts_tags pt 
                ON 
                    pt.post_id = post.post_id  

                LEFT JOIN 
                    tags tag 
                ON 
                    tag.tag_id = pt.tag_id 
                
                GROUP BY 
                    post.post_id
                ORDER BY post.post_id DESC
                LIMIT :page, :offset
            '''
            ,page = page*offset,offset = offset).dicts()

        response["pages"] = {}
        response["pages"]["current_page"] = page
        response["pages"]["location"] = '/posts'
        response["pages"]["number_of_pages"] = ceil(total_count/offset)
        response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']





# Description   :   Returns all posts
# End-point     :   /api/get/post_update_data
# Methods       :   [ POST ]
# Takes         :   page,offset and boolean all.
# Returns       :   dict with post info.

@app.route('/api/get/post_update_data', methods=['POST'])
def post_update_data():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
 
        data = request.get_json()

        response["data"] = sql(g.conn,
        '''
            SELECT 
                post.*,
                user.name as username,
                posted_by_user.name as posted_by_name,
                GROUP_CONCAT(DISTINCT tag.tag_id) as "tags"
            FROM 
                posts post 
            
            LEFT JOIN 
                users user 
            ON 
                user.user_id = post.user_id 
            
            LEFT JOIN 
                users posted_by_user 
            ON 
                posted_by_user.user_id = post.posted_by

            LEFT JOIN 
                posts_tags pt 
            ON 
                pt.post_id = post.post_id  

            LEFT JOIN 
                tags tag 
            ON 
                tag.tag_id = pt.tag_id 
            
            WHERE 
                post.post_id = :post_id
        ''',**data).dict()
        
        if not response["data"]:
            response['response']['status'] = 404
        else:
            response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




# Description   :   Returns chosen post
# End-point     :   /api/get/post/<post_name>
# Methods       :   [ POST ]
# Takes         :   post_name, and logged in user_id.
# Returns       :   dict with post data.

@app.route('/api/get/post/<post_name>',methods=['POST'])
def post(post_name):
    post_name = parse_in_like(post_name)
    print(post_name,"$$$$$$$$$$$$$$$$$$$$$$$$$$")
    # post_name+="%"
    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = {}    
        
        if request.data:
            data = request.get_json()
        else:
            data['user_id'] = -1


        response['data'] = sql(g.conn,
        '''
            SELECT 
            
                post.*,
                user.name as username,
                posted_by_user.name as posted_by_name,
                GROUP_CONCAT(DISTINCT tag.tag_name) as "tags"
            
            FROM 
                posts post 
            
            LEFT JOIN 
                users user 
            ON 
                user.user_id = post.user_id 
            
            LEFT JOIN 
                users posted_by_user 
            ON 
                posted_by_user.user_id = post.posted_by

            LEFT JOIN 
                posts_tags pt 
            ON 
                pt.post_id = post.post_id  

            LEFT JOIN 
                tags tag 
            ON 
                tag.tag_id = pt.tag_id 
            
            WHERE 
                REPLACE(REPLACE(REPLACE(REPLACE(post.title,'/',''),' ','<>'),'><',''),'<>',' ')
                Like :post_name
            GROUP by post.post_id
        '''
        ,post_name = post_name).dict()
        print("*****************************************")
        re = sql(g.conn,
        '''
            SELECT 
                * 
            FROM 
                (
                    SELECT 
                
                        COUNT(*) as "number_of_comments"
                    FROM 
                        posts_comments
                
                    WHERE 
                        post_id = :post_id
                ) pc,
                
                ( 
                    SELECT  
                        COUNT(*) as "number_of_likes"
                    FROM 
                        posts_likes
                    WHERE 
                        post_id = :post_id 
                ) pl
        '''
        ,post_id = response['data']['post_id']).dict()
        
        response['data']['likes_count'] = re['number_of_likes']
        response['data']['comments_count']= re['number_of_comments']
        
        liked = sql(g.conn,
        '''
            SELECT 

            case 
                WHEN COUNT(*)!=0 THEN "1"
                ELSE "0"
            END as "liked"

            FROM 

                posts_likes pl 

            LEFT JOIN 
                likes l 
            ON 
                l.like_id = pl.like_id 

            WHERE 
                pl.post_id = :post_id AND l.user_id = :user_id
            GROUP BY 
                pl.post_id  
        ''',user_id = data['user_id'],post_id = response['data']['post_id']).dicts()
   
        if len(liked) !=0:
            response['data']['liked'] = "1"
        else:
            response['data']['liked'] = "0"

        if not response["data"]:
            response['response']['status'] = 404
        else:
            response["post_name"] = post_name
            response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']


###################################
#[ Update ]-----------------------#
###################################

# Description   :   Updates chosen post
# End-point     :   /api/update/post
# Methods       :   [ PUT ]
# Takes         :   `post_id`, `tag_id`s, `user_id`, `title`, `text`, `image_url` 
# Returns       :   Nothing.

@app.route('/api/update/post',methods=['PUT'])
def update_post():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = request.get_json()

        post_id = int(data['post_id'])

        sql(g.conn, 
        '''

            DELETE FROM
                `posts_tags`
            WHERE 
                post_id = :post_id
        
        '''
        ,post_id = post_id)

        
        if len(data['tags'])!=0:
            vals = []
            for i in data['tags']:
                vals.append((int(post_id),int(i)))
        
            #TODO figure out multi-row insert with validation
            sql(g.conn, 
            '''
                INSERT INTO
                    `posts_tags` (`post_id`, `tag_id`) 
                VALUES 
                    {% for val in vals %} ({{val[0]}},{{val[1]}}) {% if not loop.last %}, {% endif %}{% endfor %}
            '''
            ,vals=(vals)) 

        if data['image_url'] =="":


            sql(g.conn, 
            '''
                UPDATE 
                    `posts`
                SET 
                    user_id = :user_id,
                    title = :title,
                    text = :text,
                    description = :description
                WHERE 
                    post_id = :post_id
            '''
            ,**data)
        else:
            sql(g.conn, 
            '''
                UPDATE 
                    `posts`
                SET 
                    user_id = :user_id,
                    title = :title,
                    text = :text,
                    description = :description,
                    image_url = :image_url
                WHERE 
                    post_id = :post_id         
            '''
            , **data)

     
        response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




# Description   :   Updates chosen comment
# End-point     :   /api/update/comment
# Methods       :   [ PUT ]
# Takes         :   `comment_id`, `text`
# Returns       :   Nothing.

@app.route("/api/update/comment",methods=['PUT'])
def update_comment():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        data = request.get_json()


        res = sql(g.conn,
        '''
            UPDATE 
                `comments` 
            SET 
                `text`= :text 
            WHERE 
                comment_id = :comment_id
        '''
        , **data)

        response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']



###################################
#[ Delete ]-----------------------#
###################################

# Description   :   Deletes chosen post
# End-point     :   /api/delete/post
# Methods       :   [ DELETE ]
# Takes         :   `post_id`
# Returns       :   Nothing.

@app.route('/api/delete/post',methods=['DELETE'])
def delete_post():
    
    response = {}
    response['data'] = {}
    response['response'] = {}
    
    try:
        data = request.get_json()
        sql(g.conn, '''

            DELETE 
            FROM
                `posts`
            WHERE 
                post_id = :post_id
        
            ''', **data)

        response['response']['status'] = 200
        response['response']['message'] = 'Post was deleted!' 

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']





# Description   :   Deletes chosen comment
# End-point     :   /api/delete/comment
# Methods       :   [ DELETE ]
# Takes         :   `comment_id`
# Returns       :   Nothing.

@app.route('/api/delete/comment',methods=['DELETE'])
def delete_comment():

    response = {}
    response['data'] = {}
    response['response'] = {}
    
    try:
        data = request.get_json()
        comment_id = int(data['comment_id'])


        res = sql(g.conn,
        '''

            DELETE FROM
                `comments`
            WHERE 
                comment_id = :comment_id
        '''
        , comment_id = comment_id)

        response['response']['status'] = 200
        response['response']['message'] = 'Comment was deleted!' 

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']





######################################################################
#----------------------------[ Playlist ]----------------------------#
######################################################################

###################################
#[ Create ]-----------------------#
###################################


@app.route("/api/create/playlist",methods=['POST'])
def create_playlist():
    response = {}
    response['data'] = {}
    response['response'] = {}
    try:

        result = sql(g.conn,
        '''
            SELECT playlist_id FROM playlists WHERE name = :name
        '''
        ,**g.data).dict()
        
        if not result:
            sql(g.conn,
            '''
                INSERT INTO 
                    `playlists`(`name`, `visibility`) 
                VALUES
                    ( :name , :visibility )
            '''
            ,**g.data)

            response['response']['message'] = "Added successfully!"
            response['response']['status'] = 201
        else:
            response['response']['message'] = 'Was not added!, Name conflict with playlist_id = "'+str(result["playlist_id"])+'"'            
            response['response']['status'] = 409


    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']





###################################
#[ Get ]--------------------------#
###################################

# Description   :   Returns Playlist with its tracks 
# End-point     :   /api/get/all_users
# Methods       :   [ POST ]
# Takes         :   playlist_id or name.
# Returns       :   dict with playlist and track info.

@app.route('/api/get/playlist',methods=['POST'])
def playlist():
    response = {}
    response['data'] = {}
    response['response'] = {}
    try:
        data = request.get_json()
        if 'playlist_id' in data:
            
            response['data'] = sql(g.conn,
            '''
                SELECT 
                    t.* 
                FROM 
                    tracks t
                LEFT JOIN
                    playlists_tracks p
                ON
                    p.track_id = t.track_id
                WHERE p.playlist_id = :playlist_id
            '''
            ,**data).dicts()

            response['playlist_name'] =  sql(g.conn,
            '''
                SELECT 
                    name 
                FROM 
                    playlists
                WHERE 
                    playlist_id = :playlist_id
            '''
            ,**data).scalar()


        elif 'name' in data:
            response['data'] = sql(g.conn,
            '''
                SELECT 
                    t.* 
                FROM 
                    tracks t

                LEFT JOIN
                    playlists_tracks pt
                ON
                    pt.track_id = t.track_id

                LEFT JOIN 
                    playlists p
                ON
                    p.playlist_id = pt.playlist_id

                WHERE p.name = :name
            '''
            ,**data).dicts()
            response['playlist_name'] = data['name']


        if len(response['data'])==0:
            response['response']['status'] = 404
        else:
            response['response']['status'] = 200


    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




# Description   :   Returns all Playlists
# End-point     :   /api/get/all_playlists
# Methods       :   [ POST ]
# Takes         :   page
# Returns       :   dict with playlist info.

@app.route("/api/get/all_playlists",methods=['POST'])
def get_all_playlists():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        if request.args.get('page'):
            page = int(request.args.get('page'))-1
        else:
            page = 0

        offset = 4
       
        total_count = sql(g.conn,
        '''
            SELECT 
                COUNT(*) 
            FROM 
                playlists
        '''
        ).scalar()
     

        if not request.args.get('all'):
            
            response["data"] = sql(g.conn,
            '''
                SELECT 
                    * 
                FROM 
                    playlists
                LIMIT :page, :offset
            '''
            ,page= page*offset,offset=offset).dicts()

        else:
                      
            response["data"] = sql(g.conn,
            '''
                SELECT 
                    * 
                FROM 
                    playlists
             
            '''
            ).dicts()
                
        response["pages"] = {}
        response["pages"]["current_page"] = page
        response["pages"]["location"] = '/podcasts'
        response["pages"]["number_of_pages"] = ceil(total_count/offset)
        response['response']['status'] = 200


    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




# Description   :   Returns all tracks
# End-point     :   /api/get/all_tracks
# Methods       :   [ POST ]
# Takes         :   Nothing.
# Returns       :   dict with tracks info.

@app.route("/api/get/all_tracks",methods=['POST','GET'])
def get_all_tracks():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:                
        response["data"] = sql(g.conn,
        '''
            SELECT 
                * 
            FROM 
                tracks
        '''
        ).dicts()
     
        response['response']['status'] = 200


    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




###################################
#[ Update ]-----------------------#
###################################

###################################
#[ Delete ]-----------------------#
###################################









######################################################################
#------------------------------[ Tags ]------------------------------#
######################################################################

###################################
#[ Create ]-----------------------#
###################################

# Description   :   Assigns tag to post
# End-point     :   /api/add/tag_post
# Methods       :   [ POST ]
# Takes         :   post_id and tag_id.
# Returns       :   Nothing.

@app.route('/api/add/tag_post',methods=['POST'])
def tag_post():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        result = sql(g.conn,
        '''
            SELECT * FROM posts_tags WHERE post_id = :post_id AND tag_id = :tag_id
        '''
        , **g.data).dict()

        if not result:
            response['response']['message'] = 'Was not added!,Post with post_id = "'+str(result["post_id"])+'" already has tag_id = "'+str(result["tag_id"])+'"'
            response['response']['status'] = 409
        
        else:

            sql(g.conn,
            '''
                INSERT INTO 
                    `posts_tags`(`tag_id`,`post_id`) 
                VALUES 
                    ( :tag_id , :post_id) 
            '''
            ,**g.data)

            response['response']['message'] = 'Added successfully!'
            response['response']['status'] = 201


    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']





# Description   :   Creats tag 
# End-point     :   /api/create/tag
# Methods       :   [ POST ]
# Takes         :   tag_name.
# Returns       :   Nothing.

@app.route('/api/create/tag',methods=['POST'])
def add_tag():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        result = sql(g.conn,
        '''
            SELECT 
                tag_id 
            FROM 
                tags 
            WHERE 
                tag_name = :tag_name
        '''
        ,**g.data).dict()
 
        if not result:
           
            sql(g.conn,
            '''
                INSERT INTO 
                    `tags`(`tag_name`) 
                VALUE
                    (:tag_name) 
            '''
            ,**g.data)
           
            response['response']['message'] = 'Added successfully!'
            response['response']['status'] = 201
        else:
            response['response']['message'] = 'Was not added!,Tag name conflict with tag_id = "'+str(result["tag_id"])+'"'
            response['response']['status'] = 409


    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']



###################################
#[ Get ]--------------------------#
###################################

# Description   :   Returns all tags
# End-point     :   /api/get/all_tags
# Methods       :   [ POST ]
# Takes         :   Nothing.
# Returns       :   dict with tags info.

@app.route("/api/get/all_tags",methods=['POST'])
def all_tags():
    response = {}
    response['data'] = {}
    response['response'] = {}

    try:                
        response["data"] = sql(g.conn,
        '''
            SELECT 
                * 
            FROM 
                tags
        '''
        ).dicts()
        response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']


###################################
#[ Update ]-----------------------#
###################################

# Description   :   Updates chosen tags
# End-point     :   /api/update/tag
# Methods       :   [ PUT ]
# Takes         :   tag_id, and tag_name.
# Returns       :   Nothing.

@app.route('/api/update/tag',methods=['PUT'])
def update_tag():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:
        
        sql(g.conn,
        '''
            UPDATE 
                `tags` 
            SET 
                `tag_name`= :tag_name
            WHERE 
                tag_id = :tag_id 
        '''
        ,**g.data)
            
        response['response']['message'] = 'Tag was updated!' 
        response['response']['status'] = 200

    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']


###################################
#[ Delete ]-----------------------#
###################################


# Description   :   Deletes chosen tags
# End-point     :   /api/delete/tag
# Methods       :   [ DELETE ]
# Takes         :   tag_id.
# Returns       :   Nothing.

@app.route('/api/delete/tag',methods=['DELETE'])
def delete_tag():

    response = {}
    response['data'] = {}
    response['response'] = {}

    try:

        sql(g.conn,
        '''
            DELETE FROM tags WHERE tag_id = :tag_id
        '''
        ,**g.data)

        response['response']['message'] = 'Tag was deleted!' 
        response['response']['status'] = 200

        
    except Exception as e:
        response['response']['error'] = 'Server Error!\n"'+str(e)+'"' 
        response['response']['status'] = 500
    finally:
        return response,response['response']['status']




####################################     ^   DONE    ^    ##########################################
























# End-point     :   api/""/"" 
# Description   :   ""
# Methods       :   [ "" ]
# Takes         :   ""
# Returns       :   ""
######################################################################
#----------------------------[ Template ]----------------------------#
######################################################################

###################################
#[ Create ]-----------------------#
###################################

###################################
#[ Get ]--------------------------#
###################################

###################################
#[ Update ]-----------------------#
###################################

###################################
#[ Delete ]-----------------------#
###################################


# @app.route('/api/ / ',methods=[''])
# def name():
#     response = {}
#     response['data'] = {}
#     response['response'] = {}
#     try:

#         if result:
#             response["data"] = result
#             response['response']["message"] = "successful!"
#             response['response']["status"] = 200
#         else:
#             response['response']["message"] = "unsuccessful!"
#             response['response']["status"] = 404
#         pass
#     except Exception as err :
#         response['response']["error"] = 'Server Error!\n"'+str(err)+'"' 
#         response['response']["status"] = 500
#     finally:
#         return response,response['response']["status"]
       


if __name__ == '__main__':
    app.run(host = '0.0.0.0',port=5001,debug=True)