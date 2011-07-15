# FixtureMaker

## A tool for creating Django fixtures which follow foreign key relationships.

## Quick Start Guide 
1. `pip install -e git://github.com/patjenk/FixtureMaker.git`
2. Add 'fk_fixture_maker' to your list of installed applications.
3. `python manage.py dumpdata_plus appname.ModelName --exclude=appname2.ModelName2 --exclude=appname3.ModelName3 --id=1 --id=2 --max-depth=3 --indent=2`

## Options
- --database=databasename
- --exclude=appname.ModelName
- --format=formatname
- --id=number
- --indent=number
- --max-depth=number

## Things to consider
- I don't know how this will handle circular dependencies.
