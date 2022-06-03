#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import logging
import os
import sys
from audioop import add
from datetime import datetime
from logging import FileHandler, Formatter
from operator import itemgetter

import babel
import dateutil.parser
from flask import (Flask, Response, flash, redirect, render_template, request,
                   url_for)
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import Form

from forms import *
from models import *

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime
now = datetime.now()

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  data = []

  venues = Venue.query.all()
  city_state = set()
  for venue in venues:
    city_state.add((venue.city, venue.state))

  city_state = list(city_state)
  city_state.sort(key=itemgetter(1,0))  

  for location in city_state:
    venue_list = []

    for venue in venues:
      if (venue.city == location[0]) and (venue.state == location[1]):
        num_upcoming_shows = 0 
        venue_shows = Show.query.filter_by(venue_id=venue.id).all()

        for show in venue_shows:
          if show.start_time > now:
            num_upcoming_shows += 1

        venue_list.append({
          "id": venue.id,
          "name": venue.name,
          "num_upcoming_shows": num_upcoming_shows
        })

    data.append({
      "city": location[0],
      "state": location[1],
      "venues": venue_list
    })

  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term', '').strip()

  venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()
  data = []

  for venue in venues:
    num_upcoming_shows = 0
    shows = Show.query.filter_by(venue_id=venue.id).all()

    for show in shows:
      if show.start_time > now:
        num_upcoming_shows += 1

    data.append({"id": venue.id, "name": venue.name, "num_upcoming_shows": num_upcoming_shows})

  response = {
    "count": len(venues),
    "data": data
  }

  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue = Venue.query.get(venue_id)

  if not venue:
    return redirect(url_for('index'))

  past_shows, past_shows_count = venue_past_shows(venue.shows)
  upcoming_shows, upcoming_shows_count = venue_upcoming_shows(venue.shows)

  genres = [ genre.name for genre in venue.genres ]

  data = {
    "id": venue.id,
    "name": venue.name,
    "genres": genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
    "past_shows": past_shows,
    "upcoming_shows": upcoming_shows,
    "past_shows_count": past_shows_count,
    "upcoming_shows_count": upcoming_shows_count
  }

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission(): 
  form = VenueForm()

  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data
  phone = form.phone.data
  address = form.address.data.strip()
  genres = form.genres.data
  seeking_talent = form.seeking_talent.data
  seeking_description = form.seeking_description.data.strip()
  image_link = form.image_link.data.strip()
  website = form.website_link.data.strip()
  facebook_link = form.facebook_link.data.strip()

  try:
    venue = Venue(name=name, city=city, state=state, address=address, phone=phone, 
    seeking_talent=seeking_talent, seeking_description=seeking_description, 
    image_link=image_link, website=website, facebook_link=facebook_link)
    
    for genre in genres:
        existing_genre = Genre.query.filter_by(name=genre).one_or_none()

        if existing_genre:
            venue.genres.append(existing_genre)
        else:
            new_genre = Genre(name=genre)
            db.session.add(new_genre)
            venue.genres.append(new_genre)

    db.session.add(venue)
    db.session.commit()
    flash(f"Venue '{request.form['name']}' was successfully listed!")
  except Exception as e:
    print(e)
    flash(f"An error occurred. Venue '{request.form['name']}' could not be listed.")
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  venue = Venue.query.get(venue_id)

  if not venue:
    flash(f'An error occurred. Could not find venue with ID: {venue_id}.')
    return redirect(url_for('index'))

  try:
    db.session.delete(venue)
    db.session.commit()
  except:
    flash(f'An error occurred deleting venue: {venue.name}.')
    db.session.rollback()
  finally:
    db.session.close()
  return redirect(url_for('venues'))

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = []
  artists = Artist.query.order_by(Artist.name).all()

  for artist in artists:
    data.append({
        "id": artist.id,
        "name": artist.name
    })
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '').strip()

  data = []
  artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()

  for artist in artists:
    artist_shows = Show.query.filter_by(artist_id=artist.id).all()
    num_upcoming_shows = 0

    for show in artist_shows:
      if show.start_time > now:
        num_upcoming_shows += 1

    data.append({
      "id": artist.id,
      "name": artist.name,
      "num_upcoming_shows": num_upcoming_shows
    })
  response={
    "count": len(artists),
    "data": data
  }
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist = Artist.query.filter_by(id=artist_id).first()
  shows = Show.query.filter_by(artist_id=artist_id).all()

  past_shows, past_shows_count = artist_past_shows(shows)
  upcoming_shows, upcoming_shows_count = artist_upcoming_shows(shows)

  genres = [ genre.name for genre in artist.genres ]

  data = {
    "id": artist.id,
    "name": artist.name,
    "genres": genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": past_shows,
    "upcoming_shows": upcoming_shows,
    "past_shows_count": past_shows_count,
    "upcoming_shows_count": upcoming_shows_count,
  }

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)
  if not artist:
      return redirect(url_for('index'))

  form = ArtistForm(obj=artist)
  genres = [ genre.name for genre in artist.genres ]
  
  artist_data = {
    "id": artist_id,
    "name": artist.name,
    "genres": genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link
  }
  return render_template('forms/edit_artist.html', form=form, artist=artist_data)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  form = ArtistForm()

  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data
  phone = form.phone.data
  genres = form.genres.data
  seeking_venue = form.seeking_venue.data
  seeking_description = form.seeking_description.data.strip()
  image_link = form.image_link.data.strip()
  website = form.website_link.data.strip()
  facebook_link = form.facebook_link.data.strip()

  artist = Artist.query.get(artist_id)
  try:
    artist.name = name
    artist.city = city
    artist.state = state
    artist.phone = phone
    artist.genres = []
    artist.facebook_link = facebook_link
    artist.website = website
    artist.image_link = image_link
    artist.seeking_venue = seeking_venue
    artist.seeking_description = seeking_description

    for genre in genres:
      existing_genre = Genre.query.filter_by(name=genre).one_or_none()

      if existing_genre:
          artist.genres.append(existing_genre)
      else:
          new_genre = Genre(name=genre)
          db.session.add(new_genre)
          artist.genres.append(new_genre)
    db.session.commit()
    flash(f"Artist '{request.form['name']}' was successfully updated!")
  except:
    db.session.rollback()
    flash(f"An error occurred. Artist {request.form['name']} could not be updated.")
  finally:
    db.session.close()

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get(venue_id)

  if not venue:
      return redirect(url_for('index'))

  form = VenueForm(obj=venue)
  genres = [ genre.name for genre in venue.genres ]

  venue_data = {
    "id": venue_id,
    "name": venue.name,
    "genres": genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link
  }
  return render_template('forms/edit_venue.html', form=form, venue=venue_data)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  form = VenueForm()

  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data
  address = form.address.data.strip()
  phone = form.phone.data
  genres = form.genres.data
  seeking_talent = form.seeking_talent.data
  seeking_description = form.seeking_description.data.strip()
  image_link = form.image_link.data.strip()
  website = form.website_link.data.strip()
  facebook_link = form.facebook_link.data.strip()

  venue = Venue.query.filter_by(id=venue_id).first()

  try:
    venue.name = name
    venue.city = city
    venue.state = state
    venue.address = address
    venue.phone = phone
    venue.genres = []
    venue.facebook_link = facebook_link
    venue.website = website
    venue.image_link = image_link
    venue.seeking_talent = seeking_talent
    venue.seeking_description = seeking_description

    for genre in genres:
      existing_genre = Genre.query.filter_by(name=genre).one_or_none()

      if existing_genre:
          venue.genres.append(existing_genre)
      else:
          new_genre = Genre(name=genre)
          db.session.add(new_genre)
          venue.genres.append(new_genre)

    db.session.commit()
    flash(f"Venue '{request.form['name']}' was successfully updated!")
  except:
    db.session.rollback()
    flash(f"An error occurred. Venue {request.form['name']} could not be updated.")
  finally:
    db.session.close()

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  form = ArtistForm()

  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data
  phone = form.phone.data
  genres = form.genres.data
  seeking_venue = form.seeking_venue.data
  seeking_description = form.seeking_description.data.strip()
  image_link = form.image_link.data.strip()
  website = form.website_link.data.strip()
  facebook_link = form.facebook_link.data.strip()

  try:
    artist = Artist(name=name, city=city, state=state, phone=phone,
                    facebook_link=facebook_link,
                    website=website, image_link=image_link,
                    seeking_venue=seeking_venue,
                    seeking_description=seeking_description)

    for genre in genres:
      existing_genre = Genre.query.filter_by(name=genre).one_or_none()

      if existing_genre:
          artist.genres.append(existing_genre)
      else:
          new_genre = Genre(name=genre)
          db.session.add(new_genre)
          artist.genres.append(new_genre)

    db.session.add(artist)
    db.session.commit()
    flash(f"Artist '{request.form['name']}' was successfully listed!")
  except:
    flash(f"An error occurred. Artist '{request.form['name']}' could not be listed.")
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  data = []
  shows = Show.query.all()

  for show in shows:
    data.append({
      "venue_id": show.venue_id,
      "venue_name": Venue.query.filter_by(id=show.venue_id).first().name,
      "artist_id": show.artist_id,
      "artist_name": Artist.query.filter_by(id=show.artist_id).first().name,
      "artist_image_link": Artist.query.filter_by(id=show.artist_id).first().image_link,
      "start_time": str(show.start_time)
    })
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try:
    form = ShowForm()

    artist_id = form.artist_id.data.strip()
    venue_id = form.venue_id.data.strip()
    start_time = form.start_time.data

    show = Show(artist_id=artist_id, venue_id=venue_id, start_time=start_time)

    db.session.add(show)
    db.session.commit()

    flash('Show was successfully listed!')
  except:
    flash('An error occurred. Show was unable to be created!')
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#  Custom Helpers
#  ----------------------------------------------------------------
def venue_past_shows(shows):
  past_shows = []
  for show in shows:
    if show.start_time <= now:
      past_shows.append({
        "artist_id": show.artist_id,
        "artist_name": Artist.query.get(show.artist_id).name,
        "artist_image_link": Artist.query.get(show.artist_id).image_link,
        "start_time": format_datetime(str(show.start_time))
      })
  return past_shows, len(past_shows)


def venue_upcoming_shows(shows):
  upcoming_shows = []
  for show in shows:
    if show.start_time > now:
      upcoming_shows.append({
        "artist_id": show.artist_id,
        "artist_name": Artist.query.get(show.artist_id).name,
        "artist_image_link": Artist.query.get(show.artist_id).image_link,
        "start_time": format_datetime(str(show.start_time))
      })
  return upcoming_shows, len(upcoming_shows)

def artist_past_shows(shows):
  past_shows = []
  for show in shows:
    if show.start_time <= now:
      past_shows.append({
        'venue_id' : show.venue_id,
        'venue_name' : Venue.query.get(show.venue_id).name,
        'venue_image_link': Venue.query.get(show.venue_id).image_link,
        'start_time': format_datetime(str(show.start_time))
      })
  return past_shows, len(past_shows)

def artist_upcoming_shows(shows):
  upcoming_shows = []
  for show in shows:
    if show.start_time > now:
      upcoming_shows.append({
        'venue_id' : show.venue_id,
        'venue_name' : Venue.query.get(show.venue_id).name,
        'venue_image_link': Venue.query.get(show.venue_id).image_link,
        'start_time': format_datetime(str(show.start_time))
      })
  return upcoming_shows, len(upcoming_shows)


#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
# if __name__ == '__main__':
#     app.run()

# Or specify port manually:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
