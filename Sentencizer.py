from spacy.lang.en import English

## Dict that determines where to split string based on object class type. For example, "default" will split at "Special Containment Procedures" and everything before that substring will be used for parsing.
ListTypes = {
    "default": "Special Containment Procedures",
    "ACS": "link to memo",
    "objclassbar": "Site Responsible",
    "objclassbar2": "",
    "flopsbar": "Special Containment Procedures"
}

## Object classes are normally parsed based on only the first index, the Exemptions tuple prevents this unless it is ACS or Flops Bar
Exemptions = ("Da'as Elyon", "Ein Sof", "Flor Galana", "Legally Uncontainable", "See Below")

def contentParser(sentence = "", objclass = 0):
    nlp = English()
    nlp.add_pipe("sentencizer")
    doc = nlp(sentence)
        
    ## Object Class parser, triggers if an object class type is supplied.
    if objclass != 0:
        
        ## Converts doc.sents generator to list, then filteredWords pulls just the text into a filtered list.
        wordList = list(doc.sents)[:1]
        filteredWords = [i.text for i in wordList]
            
        for words in filteredWords:
            ## Uses ListTypes dict to split at a certain point
            splitIndex = words.find(ListTypes[objclass])
            currentWords = words[:splitIndex] ## str
            
            ## Grabs first two words to check if it's in the Exemptions tuple.
            firstTwo = currentWords.split()[0:2]
            
            
            if firstTwo not in Exemptions and objclass not in ("ACS", "flopsbar"):
                filteredWords = firstTwo[0]
                return filteredWords
        
        if objclass in ("ACS", "flopsbar"):
            ## If ACS or Flops Bar, split the classes into a list and pass to MultiClassParser
            splitClasses = currentWords.split()
            classes = MultiClassParser(splitClasses, classType=objclass)
            return classes
    
    ## Description Parser, triggers if objclass is 0.
    else:
        index = 4
        while 1:
            sentences = list(doc.sents)[:index]
            filteredSentences = [i.text for i in sentences]
            parsedSentences = " ".join(i for i in filteredSentences)
            if len(parsedSentences) > 1024:
                index -= 1
            else:
                break
                    
                
        
        ## print(str(final))
        return parsedSentences
        
def MultiClassParser(classes, classType):
    
    if classType == "flopsbar":
        containment = classes[0].title()
        disruption = classes[4].title()
        risk = "flops"
        classes = containment, disruption, risk
        return classes
    
    if classes[3] == "none" or classes[3] == "{$secondary-class}":
        containment = classes[0].title()
    else:
        containment = classes[3].title()
    
    if containment.lower() not in ("pending", "uncontained", "neutralized"):
        disruption = classes[6].title()
        risk = classes[9].title()
    else:
        disruption = "None"
        risk = "None"
    
    classes = containment, disruption, risk
    return classes