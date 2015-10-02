import sys
import tempfile
import shutil
import os
import traceback
import requests

sys.path.append('/usr/local/lib/python2.7/dist-packages')
from tethys_gizmos.gizmo_options import MapView, MVLayer, MVView
from tethys_apps.sdk.gizmos import Button, TextInput,SelectInput
from hs_restclient import HydroShare, HydroShareAuthBasic
from django.http import JsonResponse
from django.shortcuts import render

def home(request):
    """
    Controller for the app home page.
    """
    # Define initial view for Map View
    view_options = MVView(
        projection='EPSG:4326',
        center=[-100, 40],
        zoom=3.5,
        maxZoom=18,
        minZoom=2
    )

    # Configure the map
    map_options = MapView(height='500px',
                          width='100%',
                          view=view_options,
                          legend=False)


     # Pre-populate lat-picker and lon_picker from model
    select_input = SelectInput(display_text='Basemap',
                            name='select_input',
                            multiple=False,
                            options=[('Bing', 'bing_layer'), ('MapQuest', 'mapQuest_layer'), ('OpenStreet', 'openstreet_layer'), ('Stamen', 'stamen_layer')],
                            original=['Bing'],
                           attributes="id=selectInput onchange=run_select_basemap()")

    txtLocation = TextInput(display_text='Location Search:',
                    name="txtLocation",
                    initial="",
                    disabled=False,
                    attributes="onkeypress=handle_search_key(event);")

    btnSearch = Button(display_text="Search",
                        name="btnSearch",
                        attributes="onclick=run_geocoder();",
                        submit=False)

    btnDelineate = Button(display_text="Delineate Watershed",
                        name="btnDelineate",
                        attributes="id=btnDelineate onclick=run_navigation_delineation_service();",
                        submit=False)

    btnDownload = Button(display_text="Download Results",
                    name="btnDownload",
                    attributes="id=btnDownload onclick=run_download_results();",
                    submit=False)



    # Pass variables to the template via the context dictionary
    context = {'map_options': map_options,
               'select_input':select_input,
               'txtLocation':txtLocation,
               'btnSearch':btnSearch,
               'btnDelineate':btnDelineate,
               'btnDownload':btnDownload,
                }



    return render(request, 'watershed_delin/home.html', context)


def upload_to_hydroshare(request):
    try:
        if request.method == 'GET':
            get_data = request.GET
            basin_kml_filetext = str(get_data['basin_kml_filetext'])
            streams_kml_filetext = str(get_data['streams_kml_filetext'])
            hs_username = str(get_data['hs_username'])
            hs_password = str(get_data['hs_password'])
            r_title = str(get_data['r_title'])
            r_type = str(get_data['r_type'])
            r_abstract = str(get_data['r_abstract'])
            r_keywords_raw = str(get_data['r_keywords'])
            r_keywords = r_keywords_raw.split(',')

            #startup a Hydroshare instance with user's credentials
            auth = HydroShareAuthBasic(username=hs_username, password=hs_password)
            hs = HydroShare(auth=auth, hostname="alpha.hydroshare.org", use_https=True)

            # try to download a tiny file simply to test the user's credentials
            # test_id = '49d01b5b0d0a41b6a5a31d8aace0a36e'
            # hs.getResource(test_id, destination=None, unzip=False)

            #download the iRODS file to a temp directory
            temp_dir = tempfile.mkdtemp()

            basin_kml_file_path = os.path.join(temp_dir, "basin.kml")
            streams_kml_file_path = os.path.join(temp_dir, "streams.kml")
            print temp_dir
            print basin_kml_file_path
            print streams_kml_file_path


            with open(basin_kml_file_path, 'w') as fd:
                    fd.write(basin_kml_filetext)
            with open(streams_kml_file_path, 'w') as fd:
                    fd.write(streams_kml_filetext)

            #upload the temp file to HydroShare
            if os.path.exists(basin_kml_file_path):
                resource_id = hs.createResource(r_type, r_title, resource_file=basin_kml_file_path, keywords=r_keywords, abstract=r_abstract)
            else:
                if temp_dir:
                    # remove the temp directory/file
                    shutil.rmtree(temp_dir)
                return JsonResponse({'error': 'An error occurred with the file upload.'})

    except Exception, err:
        #if temp_dir:
            # remove the temp directory/file
        #    shutil.rmtree(temp_dir)
        if "401 Unauthorized" in str(err):
            return JsonResponse({'error': 'Username or password invalid.'})
        elif "400 Bad Request" in str(err):
            return JsonResponse({'error': 'File uploaded successfully despite 400 Bad Request Error.'})
        else:
            traceback.print_exc()
            return JsonResponse({'error': 'HydroShare rejected the upload for some reason.'})

    # remove the temp directory/file
    #shutil.rmtree(temp_dir)
    return JsonResponse({'success': 'File uploaded successfully!',
                         'newResource': resource_id})
