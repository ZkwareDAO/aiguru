import requests
import pandas as pd
import logging

def ocr_space_file(filename, overlay=False, api_key='K81037081488957', language='eng'):
    #這是識別本地的圖片

    logging.info("inside ocr")

    payload = {'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               }
    with open(filename, 'rb') as f:
        r = requests.post('https://api.ocr.space/parse/image',
                          files={filename: f},
                          data=payload,
                          )
    return r.content.decode()


def ocr_space_url(url, overlay=False, api_key='helloworld', language='eng'):
    #這是識別網頁的圖片

    payload = {'url': url,
               'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               }
    r = requests.post('https://api.ocr.space/parse/image',
                      data=payload,
                      )
    return r.content.decode()


#這些是測試文件：
#test_url = ocr_space_url(url='https://th.bing.com/th/id/R.92b6ccf5eab31d5efdf88e3d194c5ad1?rik=HMNFqV0vCuho2w&riu=http%3a%2f%2f5b0988e595225.cdn.sohucs.com%2fimages%2f20190901%2f756cd9b3abd040e08b234e257844edaf.png&ehk=OUp7%2fUeP9WUnCfqBGBBt3c6cFpFgOIuP9WfB%2fJNooMQ%3d&risl=&pid=ImgRaw&r=0', language='eng')
#print(test_url)