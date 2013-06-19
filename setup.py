#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, glob
from distutils.core import setup
from subprocess import call

def find_mo_files():
    data_files = []
    for mo in glob.glob(os.path.join(MO_DIR, '*', 'ezame.mo')):
        lang = os.path.basename(os.path.dirname(mo))
        dest = os.path.join('share', 'locale', lang, 'LC_MESSAGES/')
        data_files.append((dest, [mo]))
    return data_files

PO_DIR = 'po'
MO_DIR = os.path.join('data', 'po')

if sys.version_info < (3, 0):
	exec_file = 'data/python2/ezame'
else:
	exec_file = 'data/python3/ezame'
data_files = [
		('share/icons/hicolor/128x128/apps', ['data/128/ezame.png']),
		('share/icons/hicolor/64x64/apps', ['data/64/ezame.png']),
		('share/icons/hicolor/32x32/apps', ['data/32/ezame.png']),
		('share/icons/hicolor/16x16/apps', ['data/16/ezame.png']),
		('share/applications/', ['data/ezame.desktop']),
		('share/ezame/', ['ezame/ezame.glade']),
		('bin/', [exec_file])]
		
for po in glob.glob(os.path.join(PO_DIR, '*.po')):
	lang = os.path.basename(po[:-3])
	mo = os.path.join(MO_DIR, lang, 'ezame.mo')
	target_dir = os.path.dirname(mo)
	if not os.path.isdir(target_dir):
		os.makedirs(target_dir)
	try:
		return_code = call(['msgfmt', '-o', mo, po])
	except OSError:
		print('Translation not available, please install gettext')
		break
	if return_code:
		raise Warning('Error when building locales')

data_files.extend(find_mo_files())
    
setup(name='ezame',
	version='0.5.1~raring',
	description='Eza\'s Menu Editor',
	author='Caldas Lopes',
	author_email='joao.caldas.lopes@gmail.com',
	url='https://launchpad.net/~caldas-lopes/+archive/ppa',
	license='GPL-3',
	packages=['ezame'],
	requires=['xdg'],
	data_files=data_files,
	)
