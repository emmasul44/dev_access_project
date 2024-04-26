import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, abort, url_for, flash
from datetime import datetime

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


# replace this with file path to where the database is on your computer
DATABASEURI = "sqlite:////Users/cindyruan/musicsite.db"
print(DATABASEURI)

#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI, connect_args={"check_same_thread": False})
print(engine)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
conn = engine.connect()
print(conn)


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
#
# see for routing: https://flask.palletsprojects.com/en/2.0.x/quickstart/?highlight=routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
# login page - first page
@app.route('/', methods=['GET', 'POST'])
def login():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: https://flask.palletsprojects.com/en/2.0.x/api/?highlight=incoming%20request%20data

  """

  # DEBUG: this is debugging code to see what request looks like
  print(request.args)
  global temp_user_id
  if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        query = text("SELECT * FROM users WHERE username = :username")
        result = g.conn.execute(query, {'username': username}).fetchone()
        if result and result[2] == password:
            # Successful login
            temp_user_id = result[0]
            return redirect(url_for('search'))
        else:
            # Failed login
            return render_template("login.html", message="Username or password is incorrect.")

  return render_template("login.html")
  

# register new user page
@app.route('/register', methods=['GET', 'POST'])
def register():
    global temp_user_id
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        query = text("SELECT * FROM users WHERE username = :username")
        result = g.conn.execute(query, {'username': username}).fetchone()

        if result:
            return render_template("register.html", message="Username already taken. Choose another.")

        query = text("SELECT max(userid) from users")
        result = g.conn.execute(query).fetchone()
        newid = int(result[0]) + 1
    
        query = text("INSERT INTO users (userid, username, password) VALUES (:userid, :username, :password)")
        g.conn.execute(query, {'userid': newid, 'username': username, 'password': password})
        g.conn.commit()

      
        return redirect(url_for('login', message="Registration successful. Please log in."))

    # Render the register.html template initially
    return render_template("register.html")

# search page after successful login
@app.route('/search', methods=['GET', 'POST'])
def search():
  if request.method == 'POST':
        search_query = request.form.get('search_query')
        search_type = request.form.get('search_type')
        if search_type == 'artist':
            query = text("SELECT * FROM artist WHERE LOWER(name) LIKE LOWER(:search_query)")
            search_results = g.conn.execute(query, {'search_query': f"%{search_query}%"}).fetchall()
        elif search_type == 'song':
            query = text("SELECT * FROM song WHERE LOWER(song_title) LIKE LOWER(:search_query)")
            search_results = g.conn.execute(query, {'search_query': f"%{search_query}%"}).fetchall()
        elif search_type == 'album':
            query = text("SELECT * FROM album WHERE LOWER(album_title) LIKE LOWER(:search_query)")
            search_results = g.conn.execute(query, {'search_query': f"%{search_query}%"}).fetchall()
        elif search_type == 'label':
            query = text("SELECT * FROM label WHERE LOWER(label_name) LIKE LOWER(:search_query)")
            search_results = g.conn.execute(query, {'search_query': f"%{search_query}%"}).fetchall()


        return render_template("search.html", search_results=search_results, search_type=search_type, search_query=search_query)
  return render_template("search.html")


# helper method for artist details page - lists songs of each album
def get_songs_for_album(album_title):
    query = text("""
        SELECT song.song_title, contains.song_order, contains.songid
        FROM album
        JOIN contains ON album.albumid = contains.albumid
        JOIN song ON contains.songid = song.songid
        WHERE album.album_title = :album_title
        ORDER BY contains.song_order
    """)
    songs = g.conn.execute(query, {'album_title': album_title}).fetchall()
    return songs

# helper method to get reviews for a song on the song details page
def get_reviews_for_song(song_title):
    query = text("""
        SELECT users.username, user_reviews_song.review, user_reviews_song.review_date, user_reviews_song.rating
        FROM song
        JOIN user_reviews_song ON song.songid = user_reviews_song.songid
        JOIN users ON user_reviews_song.userid = users.userid
        WHERE song.song_title = :song_title
        ORDER BY user_reviews_song.review_date DESC
    """)
    reviews = g.conn.execute(query, {'song_title': song_title}).fetchall()
    return reviews

# helper method to get ratings for an artist on the artist details page
def get_ratings_for_artist(name):
    query = text("""
        SELECT users.username, user_rates_artist.rating
        FROM users
        JOIN user_rates_artist ON users.userid = user_rates_artist.userid
        JOIN artist ON user_rates_artist.artistid = artist.artistid
        WHERE artist.name = :name;
    """)
    ratings = g.conn.execute(query, {'name': name}).fetchall()
    return ratings

# helper method to get ratings for an album on the album details page
def get_ratings_for_album(album_title):
    query = text("""
        SELECT users.username, user_rates_album.rating
        FROM users
        JOIN user_rates_album ON users.userid = user_rates_album.userid
        JOIN album ON user_rates_album.albumid = album.albumid
        WHERE album.album_title = :album_title;
    """)
    ratings = g.conn.execute(query, {'album_title': album_title}).fetchall()
    return ratings

# helper method to check if the the song has already been rated
def check_if_user_already_rated(userid, songid):
    query = text("SELECT COUNT(*) FROM user_reviews_song WHERE userid = :userid AND songid = :songid")
    result = g.conn.execute(query, {'userid': userid, 'songid': songid}).fetchone()

    return result[0] > 0

# helper method to check if the the artist has already been rated
def user_already_rated_artist(userid, artistid):
    query = text("SELECT COUNT(*) FROM user_rates_artist WHERE userid = :userid AND artistid = :artistid")
    result = g.conn.execute(query, {'userid': userid, 'artistid': artistid}).fetchone()

    return result[0] > 0

# helper method to check if the the album has already been rated
def user_already_rated_album(userid, albumid):
    query = text("SELECT COUNT(*) FROM user_rates_album WHERE userid = :userid AND albumid = :albumid")
    result = g.conn.execute(query, {'userid': userid, 'albumid': albumid}).fetchone()

    return result[0] > 0

# helper method to check if the the song has already been liked and added to liked playlist
def check_if_user_already_liked(userid, songid):
    query = text("SELECT COUNT(*) FROM user_likes_song WHERE userid = :userid AND songid = :songid")
    result = g.conn.execute(query, {'userid': userid, 'songid': songid}).fetchone()

    return result[0] > 0

# artist pages
@app.route('/artist/<int:artist_id>')
def artist_details(artist_id):
  artist_query = text("SELECT * FROM artist WHERE artistid = :artist_id")
  artist = g.conn.execute(artist_query, {'artist_id': artist_id}).fetchone()
  label_query = text("SELECT l.label_name, l.labelid FROM signed s JOIN label l ON s.labelid = l.labelid WHERE s.artistid = :artist_id")
  label = g.conn.execute(label_query, {'artist_id': artist_id}).fetchone()
  albums_query = text("""
        SELECT DISTINCT album.albumid, album.album_title
        FROM album
        JOIN artist_releases_album ON album.albumid = artist_releases_album.albumid
        JOIN artist ON artist_releases_album.artistid = artist.artistid
        WHERE artist.artistid = :artist_id
    """)

  albums = g.conn.execute(albums_query, {'artist_id': artist_id}).fetchall()

  if artist:
        return render_template("artist_details.html", artist=artist, albums=albums, label=label , get_songs_for_album=get_songs_for_album, get_ratings_for_artist=get_ratings_for_artist)

  return render_template("not_found.html")

# album pages
@app.route('/album/<int:album_id>')
def album_details(album_id):
    album_query = text("SELECT * FROM album WHERE albumid = :album_id")
    album = g.conn.execute(album_query, {'album_id': album_id}).fetchone()

    release_date_query = text("""
        SELECT artist_releases_album.releasedate
        FROM artist_releases_album
        WHERE artist_releases_album.albumid = :album_id
        LIMIT 1
    """)
    release_date = g.conn.execute(release_date_query, {'album_id': album_id}).fetchone()
    songs_query = text("""
        SELECT song.songid, song.song_title, contains.song_order
        FROM album
        JOIN contains ON album.albumid = contains.albumid
        JOIN song ON contains.songid = song.songid
        WHERE album.albumid = :album_id
        ORDER BY contains.song_order
    """)
    songs = g.conn.execute(songs_query, {'album_id': album_id}).fetchall()
    artist_query = text("""
        SELECT DISTINCT artist.artistid, artist.name
        FROM artist
        JOIN artist_releases_album ON artist.artistid = artist_releases_album.artistid
        WHERE artist_releases_album.albumid = :album_id
        LIMIT 1
    """)
    artist = g.conn.execute(artist_query, {'album_id': album_id}).fetchone()

    if album:
        return render_template("album_details.html", album=album, artist=artist, songs=songs, release_date=release_date, get_ratings_for_album=get_ratings_for_album)

    return render_template("not_found.html")

# song pages
@app.route('/song/<int:song_id>')
def song_details(song_id):
    song_query = text("""
        SELECT song.songid, song.song_title, song.genre, artist_releases_album.artistid, artist_releases_album.albumid
        FROM song
        JOIN artist_releases_album ON song.songid = artist_releases_album.songid
        WHERE song.songid = :song_id
    """)

    song = g.conn.execute(song_query, {'song_id': song_id}).fetchone()

    artistid = song.ArtistID
    albumid = song.AlbumID

    artist_query = text("SELECT * FROM artist WHERE artistid = :artist_id")
    artist = g.conn.execute(artist_query, {'artist_id': artistid}).fetchone()

    album_query = text("SELECT * FROM album WHERE albumid = :album_id")
    album = g.conn.execute(album_query, {'album_id': albumid}).fetchone()

    if song:
        return render_template("song_details.html", song=song, artist=artist, album=album, get_reviews_for_song=get_reviews_for_song)

    return render_template("not_found.html")

# label pages
@app.route('/label/<int:label_id>')
def label_details(label_id):
    label_query = text("SELECT * FROM label WHERE labelid = :label_id")
    label = g.conn.execute(label_query, {'label_id': label_id}).fetchone()

    artists_query = text("""
        SELECT artist.artistid, artist.name, artist.genre
        FROM artist
        JOIN signed ON artist.artistid = signed.artistid
        WHERE signed.labelid = :label_id
    """)
    artists = g.conn.execute(artists_query, {'label_id': label_id}).fetchall()

    return render_template("label_details.html", label=label, artists=artists)

# liked song playlist page
@app.route('/user')
def like_song():
    global temp_user_id

    user_query = text("SELECT * FROM users WHERE userid = :user_id")
    user = g.conn.execute(user_query, {'user_id': temp_user_id}).fetchone()

    songs_query = text("""
        SELECT song.songid, song.song_title, song.genre
        FROM song
        JOIN user_likes_song ON song.songid = user_likes_song.songid
        WHERE user_likes_song.userid = :user_id
    """)
    songs = g.conn.execute(songs_query, {'user_id': temp_user_id}).fetchall()

    return render_template("like_song.html", user=user, songs=songs)

# allows user to add song to their liked playlist
@app.route('/like', methods=['POST'])
def like(): 
  global temp_user_id
  userid = temp_user_id
  songid = request.form['songid']
  user_already_liked = check_if_user_already_liked(userid, songid)
        
  if user_already_liked:
      flash("You have already liked this song.")
      return redirect(url_for('song_details', song_id=songid))
  params_dict = {"userid":userid, "songid":songid}
  g.conn.execute(text('INSERT INTO user_likes_song(userid, songid) VALUES (:userid, :songid)'), params_dict)
  g.conn.commit()
  return redirect(url_for('song_details', song_id=songid))

# allows user to rate and review songs
@app.route('/review', methods=['POST'])
def review(): 
    global temp_user_id
    userid = temp_user_id
    songid = request.form['songid']
    review = request.form['new_review']
    review_date = datetime.now().date()

    if 'rating' in request.form:
        rating = float(request.form['rating']) / 2  
    else:
        flash("Please provide a rating before submitting a review.")
        return redirect(url_for('song_details', song_id=songid))

    user_already_rated = check_if_user_already_rated(userid, songid)
        
    if user_already_rated:
        flash("You have already rated this song.")
        return redirect(url_for('song_details', song_id=songid))

    params_dict = {
        "userid": userid,
        "songid": songid,
        "review": review,
        "review_date": review_date,
        "rating": rating,
    }
    g.conn.execute(
        text('INSERT INTO user_reviews_song(userid, songid, review, review_date, rating) VALUES (:userid, :songid, :review, :review_date, :rating)'),
        params_dict
    )
    g.conn.commit()
    
    return redirect(url_for('song_details', song_id=songid))

# allows user to rate artists
@app.route('/rate_artist', methods=['POST'])
def rate_artist(): 
  global temp_user_id
  userid = temp_user_id
  artistid = request.form['artistid']
  rating = float(request.form['rating'])/2
  user_already_rated = user_already_rated_artist(userid, artistid)
        
  if user_already_rated:
      flash("You have already rated this artist.")
      return redirect(url_for('artist_details', artist_id=artistid))
  params_dict = {"userid":userid, "artistid":artistid, "rating":rating}
  g.conn.execute(text('INSERT INTO user_rates_artist(userid, artistid, rating) VALUES (:userid, :artistid, :rating)'), params_dict)
  g.conn.commit()
  return redirect(url_for('artist_details', artist_id=artistid))

# allows users to rate albums
@app.route('/rate_album', methods=['POST'])
def rate_album(): 
  global temp_user_id
  userid = temp_user_id
  albumid = request.form['albumid']
  rating = float(request.form['rating'])/2
  user_already_rated = user_already_rated_album(userid, albumid)
        
  if user_already_rated:
      flash("You have already rated this album.")
      return redirect(url_for('album_details', album_id=albumid))
  params_dict = {"userid":userid, "albumid":albumid, "rating":rating}
  g.conn.execute(text('INSERT INTO user_rates_album(userid, albumid, rating) VALUES (:userid, :albumid, :rating)'), params_dict)
  g.conn.commit()
  return redirect(url_for('album_details', album_id=albumid))


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python3 server.py

    Show the help text using:

        python3 server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)
  app.secret_key = 'musicrocks'
  run()