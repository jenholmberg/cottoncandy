import os
import sys
import time
import datetime
import tempfile

import pytest
import numpy as np

import cottoncandy as cc

##############################
# globals
##############################
WAIT_TIME = 2.         # Account for AWS S3 lag by waiting N [seconds]
DATE = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')

prefix = 'testcc/%s/py%s'%(DATE, sys.version[:6])
object_name = os.path.join(prefix, 'test')


# login
##############################

if True:
    # for travis testing on AWS.
    bucket_name = os.environ['DL_BUCKET_NAME']
    AK = os.environ['DL_ACCESS_KEY']
    SK = os.environ['DL_SECRET_KEY']
    URL = os.environ['DL_URL']

    # test on AWS
    cci_aws = cc.get_interface(bucket_name,
                               ACCESS_KEY=AK,
                               SECRET_KEY=SK,
                               endpoint_url=URL,
                               verbose=False)

    # test on local client
    cci_local = cc.get_interface(
        os.path.join(tempfile.gettempdir(), "cottoncandy"),
        backend="local",
        verbose=False,
    )
    ALL_CCI = [cci_aws, cci_local]

elif False:
    ##############################
    # Warning
    ##############################
    # This will use your defaults to run the tests on.
    # If you use AWS, you might incur costs.
    cci = cc.get_interface()
    ALL_CCI = [cci]

else:
    # run on a local filesystem client
    cci_local = cc.get_interface(
        os.path.join(tempfile.gettempdir(), "cottoncandy"),
        backend="local",
        verbose=False,
    )
    ALL_CCI = [cci_local]
    WAIT_TIME = 0

##############################
# tests
##############################

def content_generator():
    orders = ['C','F']
    types = ['float16', 'float32', 'float64',
             'int8', 'int16', 'int32', 'int64',
             'uint8', 'uint16', 'uint32',
             'int','float']

    kinds = ['raw', 'slice', 'nonco']
    for kind in kinds:
        for order in orders:
            for dtype in types:
                print(kind, order, dtype)
                data = np.random.randn(20,10,5)
                data = np.asarray(data, order=order).astype(dtype)

                if kind == 'raw':
                    yield data
                elif kind == 'slice':
                    yield data[...,int(data.shape[0]/2):]
                elif kind == 'nonco':
                    yield data[np.random.randint(0,data.shape[0],10)]


@pytest.mark.parametrize("cci", ALL_CCI)
def test_upload_from_file(cci):
    '''test file uploads'''

    # byte round trip
    content = b'abcdefg123457890'
    flname = '/tmp/test.txt'
    with open(flname, 'wb') as fl:
        fl.write(content)

    print(cci.upload_from_file(flname, object_name=object_name))
    time.sleep(WAIT_TIME)
    dat = cci.download_object(os.path.join(prefix, 'test'))
    assert dat == content

    # string roundtrip
    content = 'abcdefg123457890'
    flname = '/tmp/test.txt'
    with open(flname, 'w') as fl:
        fl.write(content)

    print(cci.upload_from_file(flname, object_name=object_name))
    time.sleep(WAIT_TIME)
    dat = cci.download_object(os.path.join(prefix, 'test')).decode()
    assert dat == content


@pytest.mark.parametrize("cci", ALL_CCI)
def test_upload_json(cci):
    content = dict(hello=0,
                   bye='bye!',
                   )

    print(cci.upload_json(object_name, content))
    time.sleep(WAIT_TIME)
    dat = cci.download_json(object_name)
    assert dat == content
    cci.rm(object_name, recursive=True)


@pytest.mark.parametrize("cci", ALL_CCI)
def test_pickle_upload(cci):
    content = dict(hello=1,
                   bye='bye?')

    print(cci.upload_pickle(object_name, content))
    time.sleep(WAIT_TIME)
    dat = cci.download_pickle(object_name)
    assert dat == content
    cci.rm(object_name, recursive=True)

@pytest.mark.parametrize("cci", ALL_CCI)
def test_upload_npy_upload(cci):
    for content in content_generator():
        print(cci.upload_npy_array(object_name, content))
        time.sleep(WAIT_TIME)
        dat = cci.download_npy_array(object_name)
        assert np.allclose(dat, content)

@pytest.mark.parametrize("cci", ALL_CCI)
def test_upload_raw_array(cci):
    for i, content in enumerate(content_generator()):
        print(i, cci.upload_raw_array(object_name, content))
        time.sleep(WAIT_TIME)
        dat = cci.download_raw_array(object_name)
        assert np.allclose(dat, content)
        cci.rm(object_name, recursive=True)

@pytest.mark.parametrize("cci", ALL_CCI)
def test_upload_raw_array_uncompressed(cci):
    for i, content in enumerate(content_generator()):
        print(i, cci.upload_raw_array(object_name, content, compression=False))
        time.sleep(WAIT_TIME)
        dat = cci.download_raw_array(object_name)
        assert np.allclose(dat, content)
        cci.rm(object_name, recursive=True)

@pytest.mark.parametrize("cci", ALL_CCI)
def test_upload_dask_array(cci):
    for content in content_generator():
        print(cci.upload_dask_array(object_name, content))
        time.sleep(WAIT_TIME)
        dat = cci.download_dask_array(object_name)
        dat = np.asarray(dat)
        assert np.allclose(dat, content)
        cci.rm(object_name, recursive=True)


@pytest.mark.parametrize("cci", ALL_CCI)
def test_dict2cloud(cci):
    for cc in content_generator():
        content = dict(arr1=cc,
                       deep=dict(dat01=np.random.randn(15),
                                 dat02=np.random.randn(30),
                                 ),
                       )

        print(cci.dict2cloud(object_name, content))
        time.sleep(WAIT_TIME)
        dat = cci.cloud2dict(object_name)
        assert np.allclose(dat['arr1'], content['arr1'])
        for k,v in content['deep'].items():
            assert np.allclose(v, dat['deep'][k])
        cci.rm(object_name, recursive=True)
        time.sleep(WAIT_TIME)
