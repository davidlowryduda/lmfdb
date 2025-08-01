Quick Start using your browser
==============================

While logged into GitHub and viewing the `LMFDB/lmfdb` GitHub repository
(or your fork of the repository), press the comma (`,`) key on your keyboard.

Alternatively, click the green "Code" button, choose the "Codespaces" tab, and
then click "Create codesace on main".

After several minutes, a virtual machine will boot up and run a private
development server. When the text `Running on http://127.0.0.1:37777` appears,
ctrl/cmd-click the link to open it in a new tab. (Your tab will open to a URL
similar to `random-words-97vv7x9gw9h7777-37777.app.github.dev` which only you
have access to.)

You can alternatively ctrl/cmd-click the `http://127.0.0.1:37777` URL in this
readme file within your Codespace.


Installation
============

 * To develop and contribute new code, see below on
   [Sharing Your Work](https://github.com/LMFDB/lmfdb/blob/main/GettingStarted.md#code-development-and-sharing-your-work).
   If you **only** want to run a copy of the site, move into a new directory and
   type

   ```
   git clone https://github.com/LMFDB/lmfdb.git lmfdb
   ```

   and follow these instructions.

 * Make sure you have a recent version of Sage installed (at least running on Python 3)
   and that `sage` is available from the commandline.  In particular see
   [Sage installation](https://doc.sagemath.org/html/en/installation/source.html).
   Also check that your version of Sage has ssl available by checking that
   `import ssl` works on its command line. If not, then the `pip install`
   commands below will fail. To remedy this, either install SSL globally on
   your system or have Sage build its own local version, as mentioned
   [here](https://doc.sagemath.org/html/en/installation/source.html#notebook-additional-features)
   and
   [here](https://doc.sagemath.org/html/en/installation/source.html#building-the-notebook-with-ssl-support),
   respectively.

 * Install dependencies.  This requires you to have write access to the
   Sage installation directory, so should be no problem on a personal
   machine, but if you are using a system-wide Sage install on a shared
   machine, you will need ask a system administrator to do this step.

   ```
   sage -i gap_packages
   sage -i database_gap # only needed if sage version < 8.6
   sage -i pip
   sage -b
   # in the 'lmfdb/' directory:
   sage -pip install -r requirements.txt
   ```

   ### Troubleshooting with packages.

   - If you have not run the site for a while you might get an error
     with packages like

     ```
     ImportError: cannot import name monitoring
     ```

     In this case or if you need to upgrade for any reason run

     ```
     sage -pip install -r requirements.txt --upgrade
     ```
   - For versions of macOSX after 10.15 (Catalina), Sage 9.2 is unable to insall gap_packages
     (see [this](https://ask.sagemath.org/question/54252/sage92-install-gap_packages-on-macos-1015-fails/) post for some documentation on
     that). This problem does seem to be resolved for Sage 9.3beta, and it is currently
     unclear if the problem exists for Sage 9.0 or 9.1.

   - In case the last step fails by is Mac OSX with the error

     ```
     Error: pg_config executable not found.
     ```

     we recommend to installing PostgreSQL by doing

     ```
     brew install postgresql
     ```

     and performing the last step again.

   - In case the last step fails due to some missing SSL library,
     (this may be the case on osX) follow these steps

     ```
     sage -i openssl
     sage -f python2 # takes some time
     sage -i pyopenssl
     sage -pip install --upgrade pip
     sage -pip install -r requirements.txt
     ```

   - [optional] Memcache.  *This step is not at all necessary and can
     safely be ignored!* Memcache speeds up recompilation of python
     modules during development.  Using it requires both installing the
     appropriate package for your Operating System and installing an
     additional python module.  The first line below needs to be run in
     a Sage shell, and the for second you need to be a super-user to
     install memcached if your machine does not have it.

     * `easy_install -U python-memcached`

     or even better and only possible if you have the dev headers:

     * `easy_install -U pylibmc`

     * install *memcached* (e.g. ` apt-get install memcached `) and
       run the service at `127.0.0.1:11211`


Running
=======

 * A read-only copy of the database is hosted at devmirror.lmfdb.xyz. This is what is
   used by default. You can launch the webserver directly like this:

   ```
   sage -python start-lmfdb.py --debug
   ```

 * The effect of the (optional) --debug is that you will be running
   with the beta flag switched on as at dev.lmfdb.org, and also that
   if code fails your browser will show useful debugging information.
   Without `--debug` what you see will be more like www.lmfdb.org.

 * Once the server is running, visit http://localhost:37777/

   You should now have a fully functional LMFDB site through this server.

 * When running with `--debug`, whenever a python (*.py) file changes
   the server will reload automatically.  If you save while editing
   at a point where such a file is not syntactically correct, the
   server will crash and you will need to `start_lmfdb` again.   Any
   changes to html files will not cause the server to restart, so
   you will need to reload the pages in your browser.  Changes in
   the yaml files which are read only once at startup will require
   you to manually stop the server and restart it.

 * You may have to suppress loading of your local python libraries:
  `sage -python -s start-lmfdb.py`

 * If several people are running their own version of the webserver on
    the same machine, they cannot all use port 37777 -- if they try,
    they can get very confused.  In such a scenario, all involved
    should agree to using a sequence of port numbers from 37700
    upwards and allocate one such number to each user, editing
    their config.ini file with their personal port number.

 * It is possible to use a different instance of the database. For many uses,
   using the default configuration (which uses a read-only database
   on devmirror.lmfdb.xyz) is sufficient, and this step is not necessary. If you do plan
   on using a different database instance, you can do so by changing
   config.ini in the root of the lmfdb directory.


CoCalc
======

 * You can run the LMFDB inside a [CoCalc](https://www.cocalc.com) project by doing
   following the above installation instructions on a terminal in your project (you may want to
   install the requirements using the `--user` flag).
   Explicitly,

   ```
   cd ~
   git clone https://github.com/LMFDB/lmfdb.git lmfdb
   cd lmfdb
   sage -pip install --user -r requirements.txt
   sage -python start-lmfdb.py --debug
   ```

   On the last step, when you start the server running,
   LMFDB will detect that it is running inside CoCalc and provide a URL through which the
   site can be accessed.

 * If you've changed static files, you will have to run LMFDB on a different port in order for the files to update. For instance, to run LMFDB on port 37778:

   ```
   sage -python start-lmfdb.py --debug --port=37778
   ```

Troubleshooting
===============

[warning] Recently on some linux machines, users have had to install the
contents of requirements.txt by manually.  If the above instructions do not
work, un-install the above packages and re-install them one at a time,
including those in requirements.txt.


Code development and sharing your work
======================================

 * Get a (free) [github](https://github.com/) account if you do not have one
   already.

 * Login to github
 
 * If you don't already have an SSH key, you must generate a new SSH key. Once you have an SSH key
   you must add it to your GitHub account, if it isn't already added. [This documentation](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) explains how to do that.

 * Go to `https://github.com/LMFDB/lmfdb` and click on `Fork` in the upper
   right corner.

 * On your machine, create a new directory and type

   ```
   git init
   git clone git@github.com:YourGithubUserId/lmfdb.git
   ```

   using your own github user id.  Your github repository will be known
   to git as a remote called `origin`.

 * Add the (official) LMFDB repository as a remote called `upstream`.

    ```
    git remote add upstream git@github.com:LMFDB/lmfdb.git
    ```
 * To run LMFDB, go through the rest of the instructions in
   [Installation](https://github.com/LMFDB/lmfdb/blob/main/GettingStarted.md#installation) and
   [Running](https://github.com/LMFDB/lmfdb/blob/main/GettingStarted.md#running).

 * You should make a new branch if you want to work on a new feature.
   The following command creates a new branch named `new_feature` and
   switches to that branch, after first switching to the main branch
   and making sure that it is up-to-date:

   ```
   git checkout main
   git pull upstream main
   git checkout -b new_feature
   ```

 * After making your local changes, testing them and committing the
   changes, push your branch to your own github fork:

   ```
   git push -u origin new_feature
   ```

   Here, the option -u tells git to set up the remote branch
   `origin/new_feature` to be the corresponding upstream  branch you
   push to.

 * You should make sure from time to time that you pull the latest
   changes from the official LMFDB repository.  There are three
   branches upstream to be aware of: `web`, `dev` and `main`:

   - `web` is changed rarely and contains the code currently running at
     [www.lmfdb.org](www.lmfdb.org)

   - `dev` is changed more often and contains the code currently running at
     [beta.lmfdb.org](beta.lmfdb.org)

   - `main` is the development branch.

   Normal developers only need to be aware of the main
   (=development) branch.

 * To pull in the most recent changes there to your own main
   branch locally and update your github repository too:

    ```
    git checkout main
    git pull upstream main
    git push origin main
    ```

 * To rebase your current working branch on the latest main:

   ```
   git pull --rebase upstream main
   ```

 * Tell the [lmdb mailing list](https://groups.google.com/forum/#!forum/lmdb)
   that you have some new code!
   You should also issue a pull request at github
   (from your feature branch `new_feature`) at the same time.  Make
   sure that your pull request is to the lmfdb `main` branch,
   whatever your own development or feature branch is called.
   Others will review your code, and release managers will
   (eventually, if all is well) merge it into the main branch.


LMFDB On Windows
================

We do not recommend attempting to run LMFDB from within the Sage virtual image.
For anyone who would like to attempt it, the following steps should theoretically work.

 * Download `VirtualBox` and the Sage appliance, following the instructions [here](https://wiki.sagemath.org/SageAppliance).

 * The default Sage appliance does not have enough space to install LMFDB's prerequisites.  Moreover, the default
   file type (vmdk) installed by `VirtualBox` does not support resizing.  You will need to
   increase the available space by cloning into a vdi file, increasing the space and cloning back, following the
   instructions [here](https://stackoverflow.com/questions/11659005/how-to-resize-a-virtualbox-vmdk-file) and
   [here](https://www.howtogeek.com/124622/how-to-enlarge-a-virtual-machines-disk-in-virtualbox-or-vmware/).  We had
   trouble at this stage: make sure to keep the .ova file in case you screw up your virtual image.

 * The resulting disk image needs to be repartitioned to make the space available.  Unfortunately, the Sage appliance
   does not include gparted, the linux partition editor.  So, you'll need to install gparted into the appliance
   (perhaps following instructions [here](https://gembuls.wordpress.com/2011/02/12/how-to-install-epel-repository-on-centos/))
   and use it to repartition.

 * You now need to set up port forwarding so that the sage appliance can use the ports 37777 and 37010 used by lmfdb.
   See Section 6.3.1 [here](https://www.virtualbox.org/manual/ch06.html).

 * Clone the LMFDB git repository into your host OS, and set up shared folders so that you can access
   the LMFDB code from within the Sage appliance.  See the [Sage instructions](https://wiki.sagemath.org/SageAppliance) for how to share folders.

 * Now you need to run ssh-keygen within the Sage appliance and e-mail the result to Harald Schilly, Jonathan Bober or John Cremona (see above).
   Since copy-and-paste can be tricky from inside the virtual image, we suggest writing to a file shared by the host OS.

 * The instructions for Linux/OS X should now work.  You should be able to forward the mongo database and run `sage -python start-lmfdb.py` within the Sage appliance,
   and access the resulting website from your host OS' web browser.
