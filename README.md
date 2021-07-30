# decasaalcole-data

Repo to manage things around the data used by the project


## Data of this project

### Schools

#### Data sources

* ``registre.ods``: `original ODS file with schools data available [here](https://ceice.gva.es/va/web/centros-docentes/descarga-base-de-datos) at the Valencian Government web site.
 
* ``registre.vrt``: OGR virtual file for an exported CSV file of
  the Access database using [MDB Tools](http://mdbtools.sourceforge.net/).


#### How to generat the schools shapefile

* Using [mdb-tools](http://mdbtools.sourceforge.net/) and [ogr2ogr](http://www.gdal.org/ogr2ogr.html):

```bash
   $ export MDBICONV="CP1252";
   $ mdb-export REGISTRE.mdb registre > registre.csv
   $ ogr2ogr -f "ESRI Shapefile" coles.shp registre.vrt
```

### Postal Codes

#### Data sources

* TODO (@visancal)


#### Preprrocess times and distances of travel between all postal codes

* Set up a local instance of [OSRM](https://github.com/Project-OSRM/osrm-backend/wiki) with an extract of OSM from the
  zone of Valencia. The source data set is extracted with [Osmosis](https://wiki.openstreetmap.org/wiki/Osmosis) from a
  `[geofabrik Spain data](http://download.geofabrik.de/europe/spain.html).

* Coded an [script](https://github.com/jsanz/decasaalcole/blob/master/process/process_cp.py) that creates a CSV with the following structure::

    cp_from,cp_to,from_time,from_dist,to_time,to_dist

  Where ``cp_from`` is always smaller than ``cp_to``.

So the CSV stores times and distances from all postal codes. This CSV can be
joined with the postal codes and schools tables.

## CartoDB

Query to order by distance from one CP::

```sql
  with
    ftimes as (
      select
        cp_to cp,
        from_dist dist,
        from_time atime
        from times
      where cp_from = '46960'),
    ttimes as (
      select
        cp_from cp,
        to_dist dist,
        to_time atime
      from times
      where cp_to = '46960'),
    totaltimes as (
      select * from ftimes
      union select * from ttimes
      union select '46960' cp, 0 dist, 0 atime)
  select
    c.*,
    (t.atime)/60 atime,
    t.dist adist
  from coles_cp c
  join totaltimes t
  on c.cp = t.cp
  order by
    atime,
    adist
```

CartoCSS style::

  /** choropleth visualization */

```css
  #times{
    marker-fill-opacity: 0.8;
    marker-line-color: #FFF;
    marker-line-width: 0;
    marker-line-opacity: 1;
    marker-width: 10;
    marker-fill: #FFFFB2;
    marker-allow-overlap: true;
  }
  #times [ minutes <= 500] {
     marker-fill: #B10026;
  }
  #times [ minutes <= 180] {
     marker-fill: #E31A1C;
  }
  #times [ minutes <= 150] {
     marker-fill: #FC4E2A;
  }
  #times [ minutes <= 120] {
     marker-fill: #FD8D3C;
  }
  #times [ minutes <= 90] {
     marker-fill: #FEB24C;
  }
  #times [ minutes <= 60] {
     marker-fill: #FED976;
  }
  #times [ minutes <= 30] {
     marker-fill: #FFFFB2;
  }
```
