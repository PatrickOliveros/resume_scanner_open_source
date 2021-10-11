from django.http import request
from nltk.corpus.reader.tagged import TaggedCorpusReader
from resumes.models import ResumeScan
from django.shortcuts import render, redirect
from django.contrib import messages
from resume_scanner.config import proj_directory

from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords
from nltk.corpus import wordnet
from nltk.stem import PorterStemmer
import re
import string
import json
import numpy as np
from datetime import date
from nltk.stem import WordNetLemmatizer
from collections import Counter

from io import StringIO, BytesIO
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
import docx2txt

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import traceback

lemmatizer = WordNetLemmatizer()
ps = PorterStemmer()
stop_words = set(stopwords.words('english'))
year = date.today().year

with open(proj_directory+"/skills.json", "r") as read_file:
    skills_case = json.load(read_file)
    skills = list(set([skill.lower() for skill in skills_case]))
    skills_case = list(set(skills_case))

regex_phone = r"\d{3}[-\.\s]{0,3}\d{3}[-\.\s]??\d{4}|\(\d{3}\)[-\.\s]{0,3}\d{3}[-\.\s]{0,3}\d{4}"
regex_linkedin = r"[a-z]{2,3}\.linkedin\.com\/.*|linkedin\.com\/.*"
regex_email = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}"
regex_years = r"(?:\b(years experience|years)\D{0,20})([0-9,]*)[^.,]|([0-9][0-9,]*)[^.,]?(?:\D{0,20}(years experience|years))"
regex_name = r"((([A-Z][a-z]*) (\([A-Z][a-z]*\) )?(([A-Z][a-z]*-[A-Z][a-z]*)|[A-Z][a-z]*))|((([A-Z][a-z]*-[A-Z][a-z]*,)|[A-Z][a-z]*,?)( ([A-Z][a-z]*))))"
regex_address = r"(\d{3,}) ?(\w{0,5})\s([a-zA-Z]{2,30})\s([a-zA-Z]{2,15})\.?\s?(\w{0,5})"
degree_map = {
    'High School Dimploma':[' hs','high school',' ged','high school diploma'],
    "Associate's Degree":['associates','associate',"associates degree"],
    "Bachelor's Degree":['bachelor','bachelor degree',"bachelors degree",'undergrad','undergraduate',' bs'],
    "Master's Degree":['masters','masters degree',"masters degree",'graduates',"graduate's degree","graduates degree",' ms'],
    "Doctoral Degree":['doctoral','doctorate',"doctor",'phd'],
}
score_options =  {
    '0' : 'You are not an ideal fit for this job. Consider looking into a role with different required skills or in a different industry.',
    '20': "Your resume was not a great match for this job. It is possible you are missing some of the key skills required for this role. Look at the Skill Match section to see if you have any potential skill gaps.",
    '40': "Your resume was an okay match for this job. It is possible you are missing some of the key skills required for this role. Look at the Skill Match section to see if you have a potential skill gap. Don't forget to use both the acronym and full phrase in your resume.",
    '60': "Your resume was a good fit for this job. Look at the Skill Match section and the ATS Data to see if there is a way to make your resume stand out even more!",
    '80': "Your resume was a great fit for this job! Be sure to follow resume best practices to be ATS compatible!"
}

def index(request): 
    if ('resume' in request.session) and ('term' in request.session) and ('id' in request.session):
        try:
            resumescan = ResumeScan.objects.get(id = request.session['id'])
            resume = request.session['resume']
            skills_table = build_skills_table(resumescan.resume, resumescan.job, skills_case)
            output = resumescan.outputs
            score_up = 0
            for skill in skills_table:
                if skill['difference'] == True:
                    score_up = score_up+0.01
            output['lem_skill_up'] = output['lem']+score_up
            for i in output.keys():
                output[i] = str(round(output[i],4)*100)[0:5]
            # ATS Block
            if len(re.findall(regex_phone, resume)) == 1:
                phone = ('We found '+re.findall(regex_phone, resume)[0]+' in your resume. Nice job!',True)
            elif len(re.findall(regex_phone, resume)) > 1:
                phone = ('Multiple phone numbers found',False)
            else:
                phone = ('No phone found',False)
            if len(re.findall(regex_linkedin, resume)) == 1:
                linkedin = ('We found '+re.findall(regex_linkedin, resume)[0]+' in your resume. Stellar!',True)
            elif len(re.findall(regex_linkedin, resume)) > 1:
                linkedin = ('Multiple linkedin links found',False)
            else:
                linkedin = ('No linkedin found',False)
            if len(re.findall(regex_email, resume)) == 1:
                email = ('We found '+re.findall(regex_email, resume)[0]+' in your resume. Awesome formatting!',True)
            elif len(re.findall(regex_email, resume)) > 1:
                email = ('Multiple emails found',False)
            else:
                email = ('No email found',False)
            degree = degree_check(degree_map,resume,resumescan.job)
            if degree[1]:
                degree_message = 'We found '+degree[0]+' in your resume. Nice work!'
            else:
                degree_message = 'We could not find '+degree[0]+' in your resume'
            if (len(resume.split(' '))>400) and (len(resume.split(' '))<600):
                resume_length = ('Your resume is between 400 and 600 words',True)
            elif len(resume.split(' '))<400:
                resume_length = ('Your resume is less than 400 words. ('+str(len(resume.split(' ')))+' words)',False)
            elif len(resume.split(' '))>600:
                resume_length = ('Your resume is more than 600 words. ('+str(len(resume.split(' ')))+' words)',False)
            years_exp = years_exp_check(resume,resumescan.job,regex_years,year)
            if float(output['lem_skill_up']) > 100:
                output['lem_skill_up'] = 100
                output_exp = score_options['80']
            if float(output['lem_skill_up']) > 80:
                output_exp = score_options['80']
            elif float(output['lem_skill_up']) > 60:
                output_exp = score_options['60']
            elif float(output['lem_skill_up']) > 40:
                output_exp = score_options['40']
            elif float(output['lem_skill_up']) > 20:
                output_exp = score_options['20']
            else:
                output_exp = score_options['0']
            context = {
                'out':output, 
                'explanation':output_exp,
                'skills':sorted(skills_table, key = lambda i: (i['job'], i['resume']),reverse=True), 
                'ats':{
                    'phone':{'data':phone[0],'found':phone[1]},
                    'linkedin':{'data':linkedin[0],'found':linkedin[1]}, 
                    'email':{'data':email[0],'found':email[1]}, 
                    'degree_match':{'data':degree_message,'found':degree[1]},
                    'resume_length':{'data':resume_length[0],'found':resume_length[1]},
                    'years_exp':{'data':years_exp[0],'found':years_exp[1]},
                    },
                'last_resume': resume,
                }
        except Exception as e:
            context = None
    else:
        context = None
    return render(request,'index.html',context)

def scan(request): 
    if ((term_check(request) == False) or ((len(request.POST['resume']) < 1) and ('filename' not in request.FILES)) or (len(request.POST['jobpost']) < 1)):
        messages.error(request, 'Please fill out resume, job post, and terms of service')
        return redirect('/resumescanner/')
    elif 'filename' in request.FILES:
        if (request.FILES['filename'].name.endswith('.docx') or request.FILES['filename'].name.endswith('.pdf')) == False:
            messages.error(request, 'Please input a docx or pdf file')
            return redirect('/resumescanner/')
    
    if 'resume' in request.session:
        del request.session['resume']
    if 'id' in request.session:
        del request.session['id']

    try:
        if 'filename' in request.FILES:
            if request.FILES['filename'].name.endswith('.docx'):
                post_resume = read_docx(request.FILES['filename'])
            elif request.FILES['filename'].name.endswith('.pdf'):
                post_resume = read_pdf(request.FILES['filename'])
        else:
            post_resume = request.POST['resume']
    except:
        messages.error(request, 'Your resume did not parse correctly. Please try pasting it')
        return redirect('/resumescanner/')

    output = {}
    try:
        vectorizer = TfidfVectorizer(analyzer=ngram_lem, min_df = 0.1) 
        tf_idf_matrix = vectorizer.fit_transform([request.POST['jobpost']])
        indexs, scores = match_full_data(post_resume, vectorizer, tf_idf_matrix)
        output.update({'lem':scores[0]})
    except:
        output.update({'lem':0})

    post_resume = post_resume.encode("ascii", "ignore").decode("utf-8", errors="replace").replace("\x00", "\uFFFD")
    cleaned_resume = remove_demographic_data(post_resume)
    resumescan = ResumeScan.objects.create(resume = dict(Counter(cleaned_resume.split(' '))), job = request.POST['jobpost'], outputs = output)
    request.session['resume'] = str(post_resume)
    request.session['id'] = str(resumescan.id)
    request.session['term'] = True
    return redirect('/resumescanner/')

def ngram_lem(text):
    '''
    String formatter for tf-idf matrix
    '''
    text = text.lower() # lower case
    text = text.encode("ascii", errors="ignore").decode() #remove non ascii chars
    text = text.translate(str.maketrans(string.punctuation, ' '*len(string.punctuation)))
    text = re.sub(' +',' ',text).strip() # get rid of multiple spaces and replace with a single
    text = ' '+ text +' ' # pad names for ngrams...
    text = ' '.join([x for x in text.split(' ') if len(x)<15])
    text = ' '.join([x for x in text.split(' ') if one_letter_tokens(skills,x)])
    text = ' '.join([x for x in text.split(' ') if x not in stop_words])
    return [lemmatizer.lemmatize(x) for x in text.split(' ')]

def row_sender(input_name, vectorizer, tf_idf_matrix):
    '''
    Converts tf-idf matrix to index and scores
    '''
    input_name_vector = vectorizer.transform([input_name])
    result_vector = input_name_vector.dot(tf_idf_matrix.T)
    return result_vector.indices, result_vector.data

def get_top_100_match(row_ind, row_data, n_top=100):
    '''
    Returns top n tuples from a tuple with index then score by score
    '''
    n_top = len(row_ind)
    row_count = len(row_ind)
    if row_count == 0:
        return None
    elif row_count <= n_top:
        result = zip(row_ind, row_data)
    else:
        arg_idx = np.argpartition(row_data, -n_top)[-n_top:]
        result = zip(row_ind[arg_idx], row_data[arg_idx])
    return sorted(result, key=(lambda x: -x[1]))

def match_full_data(text, vectorizer, tf_idf_matrix):
    '''
    Returns top n scores and the indexs of them from tf-idf data object
    '''
    inds, rows = row_sender(text,vectorizer,tf_idf_matrix)
    matched_data = get_top_100_match(inds, rows)
    lkp_idx, lkp_sim = zip(*matched_data)
    nr_matches = len(lkp_idx)
    matched_names = np.empty([nr_matches], dtype=object)
    sim = np.zeros(nr_matches)
    indexs = []
    for i in range(nr_matches):
        sim[i] = lkp_sim[i]
        indexs.append(lkp_idx[i])
    return indexs, sim

def one_letter_tokens(skills,text):
    if len(text) > 1:
        return True
    else:
        if text in [skill.lower() for skill in skills]:
            return True
        else:
            return False

def skill_check(job_res_count, i, job, resume, skill_dict):
    add = False
    found = False
    if (len(i)<5) or (i.isupper()):
        if short_skill_checker(job, i):
            job_res_count['job'] = job.count(i)
            add = True
            if short_skill_checker(resume, i):
                job_res_count['resume'] = resume.count(i)
        if add == True:
            if (job_res_count['resume'] == 0)and(job_res_count['job'] > 0):
                job_res_count['difference'] = job_res_count['resume']-job_res_count['job']
            else:
                found = True
            skill_dict.append(job_res_count)
    else:
        if i in job:
            job_res_count['job'] = job.count(i)
            add = True
            if i in resume:
                job_res_count['resume'] = resume.count(i)
            elif i.lower() in resume.lower():
                job_res_count['resume'] = resume.lower().count(i.lower())
        elif i.lower() in job.lower():
            job_res_count['job'] = job.lower().count(i.lower())
            add = True
            if i in resume:
                job_res_count['resume'] = resume.count(i)
            elif i.lower() in resume.lower():
                job_res_count['resume'] = resume.lower().count(i.lower())
        if add == True:
            if (job_res_count['resume'] == 0)and(job_res_count['job'] > 0):
                job_res_count['difference'] = job_res_count['resume']-job_res_count['job']
            else:
                found = True
            skill_dict.append(job_res_count)
    return skill_dict, found, add

def build_skills_table(resume,job,skills):
    skill_dict = []
    for i in skills:
        job_res_count = {'skill':i,'job':0,'resume':0, 'difference':True}
        skill_dict, found, add = skill_check(job_res_count, i, job, resume, skill_dict)
        if ((len(i)>1) and (i[-1].lower() == 's') and (found == False) and (add==True)):
            job_res_count['difference'] = True
            if len(skill_dict) > 0:
                skill_dict.pop()
            skill_dict, found, add = skill_check(job_res_count, i[:-1], job, resume, skill_dict)

    new_skills = []
    for i in skill_dict:
        skip = False
        if i['skill'].isupper() == False:
            for j in skill_dict:
                if (i['skill'] in j['skill'])and(i['skill'] != j['skill']):
                    skip = True
        if skip==False:
            new_skills.append(i)
    skill_dict = new_skills
    return skill_dict

def short_skill_checker(str_j_r, skill):
    if ' '+skill+' ' in str_j_r:
        return True
    elif ' '+skill+',' in str_j_r:
        return True
    elif '\n'+skill+',' in str_j_r:
        return True
    elif '\t'+skill+',' in str_j_r:
        return True
    else:
        return False

def degree_check(degree_map,resume,job):
    try:
        resume = resume.encode("ascii", "ignore").decode().translate(str.maketrans('', '',string.punctuation))
        job = job.encode("ascii", "ignore").decode().translate(str.maketrans('', '',string.punctuation))
    except:
        resume = resume.translate(str.maketrans('', '',string.punctuation))
        job = job.translate(str.maketrans('', '',string.punctuation))
    degree = None
    for i in degree_map.keys():
        for j in degree_map[i]:
            if j in job.lower():
                degree = i
                break
    if degree:
        if degree == 'High School Dimploma':
            for key in degree_map.keys():
                for j in degree_map[key]:
                    if j in resume.lower():
                        return (degree,True)
            return (degree,False)
        elif degree == "Associate's Degree":
            for key in ["Associate's Degree","Bachelor's Degree","Master's Degree","Doctoral Degree"]:
                for j in degree_map[key]:
                    if j in resume.lower():
                        return (degree,True)
            return (degree,False)
        elif degree == "Bachelor's Degree":
            for key in ["Bachelor's Degree","Master's Degree","Doctoral Degree"]:
                for j in degree_map[key]:
                    if j in resume.lower():
                        return (degree,True)
            return (degree,False)
        elif degree == "Master's Degree":
            for key in ["Master's Degree","Doctoral Degree"]:
                for j in degree_map[key]:
                    if j in resume.lower():
                        return (degree,True)
            return (degree,False)
        elif degree == "Doctoral Degree":
            for key in ["Doctoral Degree"]:
                for j in degree_map[key]:
                    if j in resume.lower():
                        return (degree,True)
            return (degree,False)
    else:
        return ('No degree requirements found','N/A')

def years_exp_check(resume,job,regex_years,year):
    resume,job = resume.lower(),job.lower()
    finds = re.findall(regex_years, job)
    if len(finds)>0:
        year_exp = None
        for i in finds[0]:
            if i.isdigit():
                year_exp = int(i)
        if year_exp:
            for scale in range(10):
                if (str(int(year)-year_exp-scale) in resume)or(str(int(year)-year_exp-scale)[-2:] in resume):
                    return ('Your resume matched the years required. (You worked in '+str(year-year_exp)+'). Way to go!',True)
            return ('Your resume did not match the years required. (You did not work in '+str(year-year_exp)+')',False)
        else:
            return ('No years experience found on job post','Not Found')
    else:
        return ('No years experience found on job post','Not Found')

def read_pdf(file):
    output_string = StringIO()
    in_file = BytesIO(file.read())
    parser = PDFParser(in_file)
    doc = PDFDocument(parser)
    rsrcmgr = PDFResourceManager()
    device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    for page in PDFPage.create_pages(doc):
        interpreter.process_page(page)
    return output_string.getvalue()

def read_docx(file):
    in_file = BytesIO(file.read())
    out_file = docx2txt.process(in_file)
    return out_file

@api_view(['GET'])
def health(request):
    return Response({'message': 'Hello world!'}, status=status.HTTP_200_OK)

def term_check(request):
    if 'term' in request.session:
        return True
    elif 'term' in request.POST:
        return True
    else:
        return False

def remove_demographic_data(resume):
    if len(re.findall(regex_phone, resume))>0:
        phone = re.findall(regex_phone, resume)[0] 
        resume = resume.replace(phone, '')
    if len(re.findall(regex_linkedin, resume))>0:
        linkedin = re.findall(regex_linkedin, resume)[0] 
        resume = resume.replace(linkedin, '')
    if len(re.findall(regex_email, resume))>0:
        email = re.findall(regex_email, resume)[0] 
        resume = resume.replace(email, '')
    if len(re.findall(regex_name, resume))>0: 
        name = re.findall(regex_name, resume)[0][0]
        resume = resume.replace(name, '') 
    if len(re.findall(regex_address, resume))>0:
        address = re.findall(regex_address, resume)[0][0]
        resume = resume.replace(address, '') 
    return resume