clean:
	rm httpserver.log | echo 'none'
	rm parameters*.py | echo 'none'
	rm -r applications/*/compiled     | echo 'none'	
	find ./ -name '*~' -exec rm {} \; | echo 'none'
	find ./ -name '#*' -exec rm {} \; | echo 'none'
	find ./gluon/ -name '.*' -exec rm {} \; 
	find ./applications/ -name '.*' -exec rm {} \; 
	find ./ -name '*.pyc' -exec rm {} \;
backup:
	mv web2py.zip ../web2py.zip.old | echo 'none'
	cd ..; zip -r web2py.zip web2py
all:
	echo 'Version 1.49 ('`date +%Y-%m-%d\ %H:%M:%S`')' > VERSION
	### build epydoc
	rm -r applications/examples/static/epydoc/ | echo 'none'
	epydoc --config epydoc.conf
	cp applications/examples/static/title.png applications/examples/static/epydoc
	### rm all junk files
	make clean
	### clean up baisc apps
	rm applications/*/sessions/*       | echo 'none'
	rm applications/*/errors/*         | echo 'none'
	rm applications/*/cache/*          | echo 'none'        
	rm applications/admin/databases/*         | echo 'none'        
	rm applications/welcome/databases/*       | echo 'none'        
	rm applications/examples/databases/*     | echo 'none'        
	rm applications/admin/uploads/*         | echo 'none'        
	rm applications/welcome/uploads/*       | echo 'none'        
	rm applications/examples/uploads/*     | echo 'none'        
	### make admin layout and appadmin the default
	cp applications/admin/views/layout.html applications/welcome/views
	#cp applications/admin/views/layout.html applications/examples/views
	cp applications/admin/views/appadmin.html applications/welcome/views
	cp applications/admin/views/appadmin.html applications/examples/views
	cp applications/admin/controllers/appadmin.py applications/welcome/controllers
	cp applications/admin/controllers/appadmin.py applications/examples/controllers	
	### update the license
	cp ABOUT applications/admin/
	cp ABOUT applications/examples/
	cp LICENSE applications/admin/
	cp LICENSE applications/examples/
	### build the basic apps
	cd applications/admin/ ; tar cvf admin.tar *
	mv applications/admin/admin.tar ./
	cd applications/welcome/ ; tar cvf welcome.tar *
	mv applications/welcome/welcome.tar ./
	cd applications/examples/ ; tar cvf examples.tar *
	mv applications/examples/examples.tar ./
	### build web2py_src.zip
	mv web2py_src.zip web2py_src_old.zip | echo 'no old'
	cd ..; zip -r web2py/web2py_src.zip web2py/gluon/*.py web2py/gluon/contrib/* web2py/*.py web2py/*.tar web2py/ABOUT  web2py/LICENSE web2py/README web2py/VERSION web2py/Makefile web2py/epydoc.css web2py/epydoc.conf web2py/app.yaml web2py/scripts/*.sh web2py/scripts/*.py web2py/web2py.ico
app:
	rm -r dist/web2py.app | echo 'ok'
	python setup_app.py py2app
	zip -ry web2py_osx.zip dist/web2py.app
	scp web2py_osx.zip toor@140.192.34.200:~/web2py/applications/examples/static/
post:
	rsync -avz --partial --progress -e ssh web2py_src.zip toor@140.192.34.200:~/
run:
	python web2py.py -a hello
tunnel:
	ssh -L 8888:140.192.34.158:8000 -l toor 140.192.34.158
rename:
	find . -name *.html -exec grep -l Gluon {} \; | xargs perl -pi~ -e 's/Gluon/web2py/'
	find . -name '*.py' -exec grep -l Gluon {} \; | xargs perl -pi~ -e 's/Gluon/web2py/'
	find . -name *.html -exec grep -l gluon_ {} \; | xargs perl -pi~ -e 's/gluon_/web2py_/' 
	find . -name '*.py' -exec grep -l gluon_ {} \; | xargs perl -pi~ -e 's/gluon_/web2py_/' 

launchpad:
	bzr push bzr+ssh://mdipierro@bazaar.launchpad.net/~mdipierro/web2py/devel --use-existing-dir
