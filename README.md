DEPRECATED, replaced by https://github.com/datamade/chi-councilmatic
=============
City Council Legislative Subscription Service.

Contact Us
----------
- Join the mailing list at https://groups.google.com/group/councilmatic/
- Find us on irc.freenode.net in the #councilmatic room

Getting Started
---------------
First check out the project code.

    $ git clone git://github.com/codeforamerica/councilmatic.git

To work on your own instance of Councilmatic, you should first get Python
installed. Follow the instructions for doing so on your platform.

In addition, we recommend setting up a virtual environment for working with any
project, so that you can manage your project-specific dependencies.

    $ cd councilmatic
    $ virtualenv .env --no-site-packages
    $ source .env/bin/activate
    
Next, install the requirements for Councilmatic (we recommend working in a
virtual environment, but it's not strictly necessary).

    $ pip install -r requirements.txt

Non-Python requirements include:

* pdftotext and pdftohtml (use ``apt-get install poppler-utils`` on Ubuntu)


### Legislation source

Copy the file *councilmatic/local_settings.py.template* to 
*councilmatic/local_settings.py*.  Fill in the `LEGISLATION` setting in this
file.  By default, it is set up to scrape from Philadelphia's legislation
system.


### Database

Create a database for Councilmatic. Typically this is done like:

    createdb -T template_postgis councilmatic

where `template_postgis` is the name of your PostGIS database template. If you
do not yet have one, you can find instructions for getting your system ready for
Django and PostGIS online.  For example, here are instructions for 
[Mac](https://gist.github.com/3188632), and
[Ubuntu](http://brandonkonkle.com/blog/2010/jul/19/setting-template_postgis-lucid/).
For other platforms, and for further instructions, the 
[GeoDjango docs](https://docs.djangoproject.com/en/dev/ref/contrib/gis/install/#platform-specific-instructions) 
are a good place to look.

**NOTE that PostGIS 2.0 is not compatible with Django 1.4.  As Councilmatic is
currently not set up to run on Django 1.5, you should install PostGIS 1.5**


Set up the project database and populate it with city council data (when the
syncdb command prompts you to create an administrative user, go ahead and do
so). There is a lot of data to be loaded, so downloading it all may take a
while.

    $ cd councilmatic
    $ python manage.py syncdb # Create admin account when prompted.
    $ python manage.py migrate
    $ python manage.py loadlegfiles
    $ python manage.py rebuild_index # For searches. Say yes when prompted.
    $ python manage.py collectstatic # For jss and css. Say yes when prompted.


### Development server

Finally, to run the server:

    $ python manage.py runserver

Now, check that everything is working by browsing to http://localhost:8000/. Now
browse to http://localhost:8000/admin and enter the admin username and password
you supplied and you should have access to all of the legislative files!


Copyright
---------
Copyright (c) 2010 Code for America Laboratories
See [LICENSE](https://github.com/cfalabs/open311/blob/master/LICENSE.mkd) for details.

[![Code for America Tracker](http://stats.codeforamerica.org/codeforamerica/philly_legislative.png)](http://stats.codeforamerica.org/projects/philly_legislative)
