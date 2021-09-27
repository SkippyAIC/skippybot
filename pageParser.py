from __future__ import unicode_literals, print_function
import requests
from bs4 import BeautifulSoup
import os
import Sentencizer
from json import loads


class SCP:
    def __init__(self, item):
        
        ## hookDetect keyword argument disables the self.hook bool value from changing during scraping. This does not affect refined articles.
        ## includeArticleName keyword argument disables the fetching of both article name and SCP number by CROM requests.
        ## offlineOnly is made for entirely offline refined article requests.
        
        self.number = f"SCP-{item}".upper()
        self.name = ""
        self.embedName = False ## str, By changing this value, both self.number, self.name are ignored in the bot script. To include author name, include {} and use .format() later.
        self.authors = []
        self.refined = False
        self.desc = ""
        
        self.webhook = False
        self.ACS = False
        self.obj = ""
        self.flops = False
        
        self.adult = False
        self.pic = "0"
        self.url = "http://scp-wiki.wikidot.com/scp-" + item
        self.rating = 9999
        
        self.footerOverride = False
        self.hiderating = False
        self.hiderefined = False
        self.color = 0
  
        ExceptionRef = {
            "Please try again - there was a problem": "SlotGoblinException",
            "This page doesn't exist yet!": "NotExisting"
        }
        
        refinedLocation = f"bot/refined/{item}.json"
        refinedLocation = f"/home/dare/Documents/PycharmProjects/bruh/test/SCPBot/bot/refined/{item}.json"
        refinedLocation = f"C:/Users/tempa/Desktop/asscum/refined/{item}.json"
        
        cromURL = "https://api.crom.avn.sh/graphql"
        
        query = '''{
  page(url: "URLReplace") {
    wikidotInfo{
      thumbnailUrl
      rating
      tags
    }
    attributions{
      user{
        name
      }
    }
    alternateTitles{title}
  }
}'''
        
        if not os.path.exists(refinedLocation):
            ## Grabs URL and checks if it is an adult article, also uses requests.get to get article URL post-redirect.
            res = requests.get(self.url, allow_redirects=True)
            if "This article contains adult content" in res.text:
                
                self.adult = True
                
                cromCompatURL = self.url.replace(".com/scp-", ".com/adult:scp-")
                self.url = cromCompatURL + "/noredirect/true"
                self.embedName = self.number + "{}"
                res = requests.get(self.url)
            else:
                cromCompatURL = self.url
                self.url = res.url.replace("https", "http")
            
            ## Sets up CROM request, uses string methods to insert URL.
            query = query.replace("URLReplace", cromCompatURL)
            json = {"query": query}

    
        ## Article Refinement System
        if os.path.exists(refinedLocation):
            with open(refinedLocation, "r") as f:
              refinedJSON = loads(f.read())
              
              """
              {"name": str, article name
              "number": str, scp-number
              "embedName": optional str, using this will ignore name, number, and author values, instead filling in the embedName with this value. to include author names, include {} and use .format later.
              "desc": str,
              "authors": JSON array
              "hook": bool by default, JSON array with name and img url
              "acs": bool,
              "flops": bool,
              "pic": str, url by default, str "0" if no pic,
              "class": str, comma separated string if acs or flops, if flops then put obj and disrupt classes, and the final value as "flops"
              "adult": bool,
              "url": str, if not offlineOnly then must be http and no "www."
              "color": optional hex as str, force embed color. by default, colorChecker() will handle this based on the Object Class.
              "footer": optional str, define custom footer in place of random quote,
              "rating": optional int, **USE THIS WITH CARE!** forces rating number. by not including this key, pageParser will request the current rating from CROM. to hide the rating number, enter rating int as 9999.,
              "hiderefined": optional bool, hide 'refined by dev' text in embed."""
              
              try:
                self.rating = refinedJSON["rating"]
              except KeyError:
                query = query.replace("URLReplace", refinedJSON["url"])
                json = {"query": query}
                livePage = requests.post(cromURL, json=json).json()
                self.rating = livePage["data"]["page"]["wikidotInfo"]["rating"]
                pass
                    
              
              self.name = refinedJSON["name"]
              self.number = refinedJSON["number"]
              self.refined = True
              self.desc = refinedJSON["desc"].replace("\\n", "\n")
              
              if "embedName" in refinedJSON:
                self.embedName = refinedJSON["embedName"]
              
              self.authors = refinedJSON["authors"]
              
              if not isinstance(refinedJSON["hook"], list):
                self.webhook = bool(refinedJSON["hook"])
              else:
                self.webhook = refinedJSON["hook"]
                
              self.ACS = bool(refinedJSON["acs"])
              
              if self.ACS:
                self.obj = tuple(refinedJSON["class"].split(", "))
              else:
                self.obj = refinedJSON["class"]
              
              self.adult = bool(refinedJSON["adult"])
              self.pic = refinedJSON["pic"]
              self.url = refinedJSON["url"]
              if "color" in refinedJSON:
                self.color = int(refinedJSON["color"], 16)
              if "footer" in refinedJSON:
                self.footerOverride = refinedJSON["footer"]
              if "rating" in refinedJSON:
                self.rating = refinedJSON["rating"]
              if "hiderefined" in refinedJSON:
                self.hiderefined = refinedJSON["hiderefined"]
              
              return
    
        ## If there is no .json file for the SCP, it proceeds to parse the current webpage.
        
        ## Makes CROM request and makes new var for easier access
        cromRequest = requests.post(cromURL, json=json).json()
        cromData = cromRequest["data"]["page"]
        
        if cromData["wikidotInfo"] is None:
            self.desc = "NotExisting"
            self.obj = "NotExisting"
            return
        

        if not self.adult:
            self.name = cromData["alternateTitles"][0]["title"]
        
        self.rating = cromData["wikidotInfo"]["rating"]
        
        for author in cromData["attributions"]:
            self.authors.append(author["user"]["name"])
        
        image = cromData["wikidotInfo"]["thumbnailUrl"]
        if image is not None:
            self.pic = image
        
        
        ## Uses BeautifulSoup to remove footnote numbers from the page.
        html_page = res.content
        soup = BeautifulSoup(html_page, 'html.parser')
        for div in soup.find_all("sup", {'class': 'footnoteref'}):
            div.decompose()
    
                
        text = soup.find_all(text=True)
        
        ## Further filters page
        output = ""
        blacklist = [
            '[document]'
            'noscript',
            'header',
            'html',
            'meta',
            'head',
            'input',
            'script'
        ]
        for t in text:
            if t.parent.name not in blacklist:
                output += f"{t} "
        
        ## Fixes colon error in document
        if "Description : " in output or "Object Class : " in output:
            output = output.replace(" : ", ":  ")
        
        ## Fixes capitalization for easier parsing.
        if "DESCRIPTION:" in output:
            output = output.replace("DESCRIPTION", "Description").replace("SPECIAL CONTAINMENT PROCEDURES", "Special Containment Procedures")
        
        ## Attempts to find "Description:" substring and filters out leading \n's and filters out double spaces. If unable to find, the ExceptionRef dict is scanned to see if a Wikidot error occurred or if the page does not exist. If neither, it is assumed the article has a format quirk, and a FormattingException is returned.
        for substring in ("Description: ", "Description"):
            try:
                desc = output.split(substring)[1].strip()
                desc = desc.replace("  ", " ").replace(" . ", ". ")
                break
            except Exception:
                continue
        
        if "desc" not in locals():
            print("i shit myself")
            for key in ExceptionRef.keys():
                if key in output:
                    self.obj = ExceptionRef[key]
                    break
                else:
                    self.obj = "FormattingException"
            return
        
        ## Passes desc to Sentencizer. and improves spacing between paragraphs.
        self.desc = Sentencizer.contentParser(sentence=desc)
        self.desc = self.desc.replace("\n", "\n\n")
        
        ## Fun webhook stuffs, detects if article is a Broken Masquerade article and adjusts username and profile pic accordingly. This can be disabled by creating an SCP object with hookDetect=0
        if "broken-masquerade" in output:
            self.webhook = ("Skippy.aic || Safety Continues in Public", r"https://cdn.discordapp.com/avatars/865268366360576020/332b561de001fed9f6f2679f25997818.webp?size=128%22")
        
        ## If/Elif to detect what type of object class system is used.
        if "Risk Class:" in output:

            try:
                ObjectClass = output.split("Containment Class: \n ")[1]
            except Exception:
                ObjectClass = output.split("Containment Class: ")[1]
                if "# /" in ObjectClass:
                    ObjectClass = ObjectClass.replace("# /", "")
            self.obj = Sentencizer.contentParser(ObjectClass, "ACS")
            
            ## When Neutralized is used in ACS, no other classes are used. It is treated the same as a default Object Class system string instead of a tuple.
            if "Neutralized" in self.obj:
                self.obj = self.obj[0]
            else:
                self.ACS = True
        
        elif "DISRUPTION CLASS: " in output:
            ObjectClass = output.split("CONTAINMENT CLASS: ")[1]
            self.obj = Sentencizer.contentParser(ObjectClass, "flopsbar")
            self.flops = True
        
        elif "Site Responsible:" in output:
            ObjectClass = output.split("Object Class: ")[1]
            self.obj = Sentencizer.contentParser(ObjectClass, "objclassbar")
        
        elif "classified-bar" in output:
            ObjectClass = output.split(f"Item #: SCP-{item}")[1]
            self.obj = ObjectClass[7:20].strip().title()
        
        else:
            ## Final check for object class type, checks default classes. If none are present, SCP.desc and SCP.obj return FormattingException.
            try:
                classFound = 0
                for val in ("Containment Class: ", "Anomaly Class: ", "Object Class: "):
                    if val in output:
                        ObjectClass = output.split(val)[1]
                        self.obj = Sentencizer.contentParser(ObjectClass, "default")
                        classFound = 1
                        break
                if not classFound:
                    raise Exception
            except Exception:
                print("FormattingException")
                self.desc = "FormattingException"
                self.obj = "FormattingException"
    
if __name__ == "__main__":
    from sys import argv
    x = SCP(argv[1])
    print(x.desc)