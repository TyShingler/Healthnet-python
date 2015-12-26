from datetime import datetime
from django.http import HttpResponse
from django import forms
from django.contrib import auth
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.core import serializers
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils import timezone
from .forms import AppointmentForm, EditProfileForm, MessageForm, MedicalTestForm, NotificationForm, PersonLoginForm, \
    PrescriptionForm, RegisterForm, UploadPatientForm, UpdatePatientForm, UpdateTestForm, UpdateUsertypeForm
from .models import Activity, Appointment, Message, Notification, Person, Prescription, MedicalTest, SystemStats
import json
import re
import time


# Directs user to either /login or /dashboard depending on their logged-in status
def index(request):
    if Person.objects.all().count() == 0:
        createData()
    if request.user.is_authenticated():
        return redirect('/dashboard/')
    else:
        return redirect('/login/')


# The main screen that displays calendar and appointments
def dashboard(request):
    if not request.user.is_authenticated():
        return redirect('/login/')

    if request.user.person.usertype == 'admin':
        return redirect('/adminpanel/')

    user = request.user.person
    notes = getNotifications(user)
    listOptions = Person.objects.filter(preferred_hospital=user.preferred_hospital).exclude(usertype='nurse')
    appointments = []
    if user.usertype == 'patient':
        appointments = Appointment.objects.filter(p_username=user.username)
    elif user.usertype == 'doctor':
        appointments = Appointment.objects.filter(doctor=user.last_name)
    elif user.usertype == 'nurse':
        appointments = Appointment.objects.filter()

    return render(request, 'dashboard.html', {'createForm': AppointmentForm(prefix="create"),
                                              'deleteForm': AppointmentForm(prefix="delete"),
                                              'notifications': notes, 'listOptions': listOptions,
                                              'appointments': appointments, 'user': user})


#login screen that prompts user for their username and password
def userLogin(request):
    if Person.objects.all().count() == 0:
        createData()
    if request.user.is_authenticated():
        return redirect('/dashboard/')

    if request.method == 'POST':
        form = PersonLoginForm(request.POST)
        user = auth.authenticate(username=request.POST.get('username'), password=request.POST.get('password'))
        if user is not None:
            if user.is_active:
                login(request, user)
                activity = Activity(data=user.username + " logged in",
                                    date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
                activity.save()
                stats = SystemStats.objects.filter()[0]
                stats.successfulLogins += 1
                stats.save()
                return redirect('/')
        else:
            stats = SystemStats.objects.filter()[0]
            stats.failedLogins += 1
            stats.save()
            return render(request, 'login.html', {'form': PersonLoginForm, 'errors': form.errors})

    return render(request, 'login.html', {'form': PersonLoginForm})


def userLogout(request):
    logout(request)

    return redirect('/')


def userRegister(request):
    global form
    if Person.objects.all().count() == 0:
        createData()
    if request.user.is_authenticated():
        return redirect('/dashboard/')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            cleanData = form.cleaned_data
            user = User.objects.create_user(username=cleanData['username'], email=cleanData['email'],
                                            password=cleanData['password'], first_name=cleanData['first_name'].title(),
                                            last_name=cleanData['last_name'].title())
            person = Person(person=user, phone=re.sub("[^0-9]", "", cleanData['phone']),
                            birthdate=cleanData['birthdate'], first_name=cleanData['first_name'].title(),
                            last_name=cleanData['last_name'].title(), email=cleanData['email'],
                            username=cleanData['username'], usertype='patient', sex=cleanData['sex'],
                            preferred_hospital=cleanData['preferred_hospital'], primary_physician='none',
                            last_physical=cleanData['last_physical'], health_history='Empty', status='Discharged')

            primphys = Person.objects.filter(usertype='doctor', preferred_hospital=person.preferred_hospital)[0]
            person.primary_physician = "Dr. " + primphys.last_name
            user.save()
            user = auth.authenticate(username=request.POST.get('username'), password=request.POST.get('password'))
            person.save()

            activity = Activity(data=user.username + " registered",
                                    date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
            activity.save()
            login(request, user)
            activity = Activity(data=user.username + " logged in",
                                date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
            activity.save()
            stats = SystemStats.objects.filter()[0]
            stats.totalPatients += 1
            stats.save()

            return redirect('/')
        else:

            return render(request, 'register.html', {'form': RegisterForm, 'errors': form.errors})

    return render(request, 'register.html', {'form': RegisterForm})


def profileView(request):
    if not request.user.is_authenticated():
        return redirect('/login/')

    user = request.user.person
    notes = getNotifications(user)

    return render(request, 'profile.html', {'user': user, 'notifications': notes})


def profileEdit(request):
    if not request.user.is_authenticated():
        return redirect('/login/')

    person = request.user.person
    notes = getNotifications(person)
    if request.method == 'POST':
        if not Person.objects.filter(email=request.POST.get('email')).count() > 0 \
                or request.POST.get('email') == request.user.person.email:

            form = EditProfileForm(request.POST)

            if form.is_valid():
                cleanData = form.cleaned_data

                person.first_name = cleanData['first_name'].title()
                person.last_name = cleanData['last_name'].title()
                person.email = cleanData['email'].replace('>', '').replace('<', '')
                person.birthdate = cleanData['birthdate'].replace('>', '').replace('<', '')
                person.sex = cleanData['sex'].replace('>', '').replace('<', '')
                person.phone = cleanData['phone'].replace('(', '').replace(')', '').replace('-', '').replace(' ','')
                person.health_history = cleanData['health_history']
                person.last_physical = cleanData['last_physical']
                person.save()
                activity = Activity(data=person.username + " edited their profile",
                                    date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
                activity.save()

                return redirect('/profile/')
            else:
                return redirect('/editprofile/',
                                {'form': EditProfileForm, 'errors' : form.errors, 'notifications': notes})

    return render(request, 'editprofile.html',
                  {'form': EditProfileForm, 'user': person, 'notifications': notes})


def createAppointment(request):
    if not request.user.is_authenticated():
        return redirect('/login/')

    if request.method == 'POST':
        form = AppointmentForm(request.POST, prefix="create")
        form.is_valid()
        user = request.user.person
        cleanData = form.cleaned_data
        if not 'description' in cleanData:
            return redirect('/dashboard/')
        atime = cleanData['time']
        datetime = cleanData['date'] + "T" + atime

        if int(atime[:2]) < 8 or int(atime[:2]) >= 17:
            return redirect('/dashboard/')

        aptcompare = None
        if user.usertype == "doctor":
            aptcompare = Appointment.objects.filter(doctor=user.last_name)
        else:
            aptcompare = Appointment.objects.filter(doctor=cleanData['doctor'].replace("Dr. ",""))

        for item in aptcompare:
            if (str(item.date)[:16]) == (datetime.replace("T"," ")):
                return redirect('/dashboard/')

        today = time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S")
        notification = Notification(type='appointment', date=today, user=user.username, data=cleanData['date'])

        activity = None
        appointment = None
        if user.usertype == "patient":
            notification.doctor = cleanData['doctor'].replace("Dr. ","")
            notification.data2 = user.first_name + " " + user.last_name + " (" + user.username + ")"
            appointment = Appointment(doctor=cleanData['doctor'].replace('<', '').replace("Dr. ",""), date=datetime,
                                      description=cleanData['description'].replace('<', '').replace('>', ''),
                                      p_username=user.username, p_first_name=user.first_name,
                                      p_last_name=user.last_name, hospital=user.preferred_hospital)
            activity = Activity(data=user.username + " created an appointment with " + cleanData['doctor'],
                                date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))

        elif user.usertype == "doctor":
            notification.doctor = user.last_name
            notification.data2 = cleanData['p_first_name']
            splitString = cleanData['p_first_name'].replace("(","").replace(")","").split()
            appointment = Appointment(doctor=user.last_name, date=datetime,
                                      description=cleanData['description'].replace('<', '').replace('>', ''),
                                      p_username=splitString[2], p_first_name=splitString[0],
                                      p_last_name=splitString[1], hospital=Person.objects.filter(username=splitString[2])[0].preferred_hospital)
            activity = Activity(data=user.username + " created an appointment with " + splitString[2],
                                date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
        else:
            notification.doctor = cleanData['doctor']
            notification.data2 = cleanData['p_first_name']
            splitString = cleanData['p_first_name'].replace("(","").replace(")","").split()
            appointment = Appointment(doctor=cleanData['doctor'], date=datetime,
                                      description=cleanData['description'].replace('<', '').replace('>', ''),
                                      p_username=splitString[2], p_first_name=splitString[0],
                                      p_last_name=splitString[1], hospital=Person.objects.filter(username=splitString[2])[0].preferred_hospital)
            activity = Activity(data=user.username + " created an appointment for " + splitString[2] + " to meet with "
                                     + cleanData['doctor'],
                                date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
        notification.save()
        activity.save()
        appointment.save()
        stats = SystemStats.objects.filter()[0]
        stats.appointmentsCreated += 1
        stats.save()

    return redirect('/dashboard/')


def deleteAppointment(request, id):
    if not request.user.is_authenticated() or \
                    request.user.person.usertype == 'nurse':
        return redirect('/login/')

    if request.method == 'POST':
        form = AppointmentForm(request.POST, prefix="delete")
        Appointment.objects.filter(pk=id).delete()
        activity = Activity(data=request.user.person.username + " deleted an appointment",
                            date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
        activity.save()

    return redirect(request.META['HTTP_REFERER'].replace("http://localhost:8000",""))


def editAppointment(request, id):
    print("")
    if request.method == 'POST':
        user = request.user.person
        form = AppointmentForm(request.POST, prefix="delete")
        form.is_valid()
        cleanData = form.cleaned_data

        if not 'description' in cleanData:
            return redirect('/dashboard/')

        atime = cleanData['time']
        datetime = cleanData['date'] + "T" + atime
        print(atime)
        print(datetime)
        if int(atime[:2]) < 8 or int(atime[:2]) >= 17:
            print("time redirect")
            return redirect(request.META['HTTP_REFERER'].replace("http://localhost:8000",""))

        aptcompare = None
        if user.usertype == "doctor":
            aptcompare = Appointment.objects.filter(doctor=user.last_name, date=datetime.replace("T"," ")).exclude(pk=id)
        else:
            aptcompare = Appointment.objects.filter(doctor=cleanData['doctor'].replace("Dr. ",""),
                                                    date=datetime.replace("T"," ")).exclude(pk=id)

        if len(aptcompare) >= 1:
            return redirect(request.META['HTTP_REFERER'].replace("http://localhost:8000",""))

        apt = Appointment.objects.get(pk=id)
        apt.doctor = cleanData['doctor'].replace("Dr. ","")
        apt.date = datetime
        apt.description = cleanData['description']
        apt.save()
        activity = Activity(data=user.username + " edited an appointment",
                            date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
        activity.save()

    return redirect(request.META['HTTP_REFERER'].replace("http://localhost:8000",""))


#Creates a text file of information in patient's profile
def exportUser(request, id):

    export_data = str(Person.objects.filter(pk=id))

    response = HttpResponse(export_data, content_type='application/txt')
    response['Content-Disposition'] = 'attachment; filename=' + request.user.person.user_export_fileName() + '.txt'

    # make sure the function ends with this.
    return redirect('/userlist/')


def appointments(request):
    if not request.user.is_authenticated():
        return redirect('/login/')

    user = request.user.person
    appointments = []
    notes = getNotifications(user)
    listOptions = Person.objects.filter().exclude(usertype='nurse')
    if user.usertype == 'patient':
        appointments = Appointment.objects.filter(p_username=user.username)
    elif user.usertype == 'doctor':
        appointments = Appointment.objects.filter(doctor=user.last_name)
    elif user.usertype == 'nurse':
        appointments = Appointment.objects.filter()

    return render(request, 'appointments.html', {'user': user, 'appointments': appointments, 'notifications': notes,
                                                 'options': listOptions, 'form': AppointmentForm(prefix="delete")})


def prescribe(request):
    if not request.user.is_authenticated() or \
                    request.user.person.usertype == 'patient':
        return redirect('/login/')

    user = request.user.person
    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        form.is_valid()
        cleanData = form.cleaned_data
        today = time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S")
        prescription = Prescription(doctor="Dr. " + user.last_name, patient=cleanData['patient'],
                                    drugname=cleanData['drugname'].title(), description=cleanData['description'],
                                    dosage=cleanData['dosage'], quantity=cleanData['quantity'],
                                    instructions=cleanData['instructions'])
        prescription.save()
        print(cleanData['patient'])
        notification = Notification(type='prescription', date=today, user=cleanData['patient'],
                                    doctor=user.last_name, data=cleanData['drugname'].title())
        notification.save()
        activity = Activity(data=user.username + " prescribed a medication to " + cleanData['patient'],
                            date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
        activity.save()
        stats = SystemStats.objects.filter()[0]
        stats.medicationsPrescribed += 1
        stats.save()

    patients = Person.objects.filter(usertype='patient')
    notes = getNotifications(user)

    return render(request, 'prescribe.html', {'user': request.user.person, 'patients': patients,
                                              'form': PrescriptionForm, 'notifications': notes})


def prescriptions(request):
    if not request.user.is_authenticated() or \
                    request.user.person.usertype == 'nurse' or \
                    request.user.person.usertype == 'doctor':
        return redirect('/login/')

    user = request.user.person
    username = user.first_name + " " + user.last_name + " (" + user.username + ")"
    prescripts = Prescription.objects.filter(patient=username)
    notes = getNotifications(user)

    return render(request, 'prescriptions.html', {'user': request.user.person, 'prescriptions': prescripts,
                                                  'notifications': notes})

def removeprescription(request):
    if not request.user.is_authenticated() or request.user.person.usertype == 'patient':
        return redirect('/login/')

    user = request.user.person
    prescripts = Prescription.objects.filter(doctor="Dr. " + user.last_name)
    notes = getNotifications(user)

    return render(request, 'removeprescription.html', {'user': request.user.person, 'prescriptions': prescripts,
                                                  'notifications': notes})


def removeprescript(request, id):
    if not request.user.is_authenticated() or request.user.person.usertype == 'patient':
        return redirect('/login/')

    Prescription.objects.filter(pk=id).delete()
    return redirect('/removeprescription')

def testresults(request):
    if not request.user.is_authenticated():
        return redirect('/login/')

    user = request.user.person
    notes = getNotifications(user)
    tests = MedicalTest.objects.filter(patient=user.username)
    return render(request, 'testresults.html', {'user': request.user.person, 'notifications': notes,
                                                'form': MedicalTestForm, 'tests': tests})


def pendingtests(request):
    if not request.user.is_authenticated():
        return redirect('/login/')

    user = request.user.person
    notes = getNotifications(user)
    tests = MedicalTest.objects.filter(pending='true')
    return render(request, 'pendingtests.html', {'user': user, 'notifications': notes, 'tests': tests,
                                                 'form': UpdateTestForm})


def returnresults(request, id):
    if not request.user.is_authenticated() or request.user.person.usertype == 'patient':
        return redirect('/login/')

    if request.method == 'POST':
        user = request.user.person
        form = UpdateTestForm(request.POST)
        if form.is_valid():
            cleanedData = form.cleaned_data
            test = MedicalTest.objects.filter(pk=id)[0]
            test.results = cleanedData['results']
            test.pending = 'false'
            test.save()

            from twilio.rest import TwilioRestClient
            account_sid = 'ACe212fa202fc8eda023a8103d97b9f7e4'
            auth_token = '84e58d6c5791812287efe0d8c9cea55c'
            client = TwilioRestClient(account_sid, auth_token)
            client.messages.create(to="+1" + Person.objects.filter(username=test.patient)[0].phone,
                                   from_='+16502156528', body='You have received test results!')

            today = time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S")
            notification = Notification(type='medicalresult', date=today, user=test.patient,
                                    doctor='None', data=test.testname)
            notification.save()
            activity = Activity(data=user.username + " returned test results to " + test.patient,
                            date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
            activity.save()
            stats = SystemStats.objects.filter()[0]
            stats.testsConducted += 1
            stats.save()

    return redirect('/pendingtests/')


def requesttest(request):
    if not request.user.is_authenticated() or request.user.person.usertype != 'patient':
        return redirect('/login/')

    if request.method == 'POST':
        user = request.user.person
        form = MedicalTestForm(request.POST)
        if form.is_valid():
            cleanedData = form.cleaned_data
            today = time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S")
            test = MedicalTest(testname=cleanedData['testname'], patient=user.username, date=today, pending='true')
            test.save()

            notification = Notification(type='medicaltest', date=today, user=user.username,
                                    doctor='NULL', data=cleanedData['testname'].title())
            notification.save()
            activity = Activity(data=user.username + " requested a medical test",
                            date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
            activity.save()

    return redirect('/testresults/')

def medicalhistory(request):
    if not request.user.is_authenticated() or request.user.person.usertype != 'patient':
        return redirect('/login/')

    user = request.user.person
    notes = getNotifications(user)
    tests = MedicalTest.objects.filter(patient=user.username)
    query = user.first_name + " " + user.last_name + " (" + user.username + ")"
    prescripts = Prescription.objects.filter(patient=query)

    return render(request, 'medicalhistory.html', {'user': request.user.person, 'notifications': notes,
                                                   'tests': tests, 'prescriptions': prescripts})


#Allows doctors to see a list of all users in the system
def patientlist(request):
    if not request.user.is_authenticated() or \
                    request.user.person.usertype == 'patient':
        return redirect('/login/')

    user = request.user.person
    notes = getNotifications(user)
    patients = Person.objects.filter(usertype='patient')
    prescriptions = Prescription.objects.filter()
    doctors = Person.objects.filter(usertype='doctor')
    admitted = Person.objects.filter(usertype='patient', status='Admitted').count()

    return render(request, 'patientlist.html', {'user': user, 'patients': patients, 'notifications': notes,
                                                'prescriptions': prescriptions, 'form': UpdatePatientForm,
                                                'doctors': doctors, 'admitted': admitted})


def updatepatient(request, id):

    form = UpdatePatientForm(request.POST)
    if form.is_valid():
        cleanData = form.cleaned_data
        patient = Person.objects.filter(pk=id)[0]
        patient.primary_physician = cleanData['u_primary_physician']
        dr = Person.objects.filter(usertype='doctor', last_name=cleanData['u_primary_physician'].replace("Dr. ",""))[0]
        patient.last_physical = cleanData['u_last_physical']
        patient.health_history = cleanData['u_health_history']
        patient.preferred_hospital = cleanData['u_preferred_hospital']

        if not patient.preferred_hospital == dr.preferred_hospital:
            patient.preferred_hospital = dr.preferred_hospital

        patient.save()

    return redirect('/userlist/')


def notifications(request):
    if not request.user.is_authenticated():
        return redirect('/login/')

    user = request.user.person
    notes = getNotifications(user)
    notifications = []
    if user.usertype == 'patient':
        notifications = Notification.objects.filter(Q(type='appointment', user=user.username) |
                                                    Q(type='message', doctor=user.username) |
                                                    Q(type='prescription'))
    elif user.usertype == 'doctor':
        notifications = Notification.objects.filter(Q(type='appointment', doctor=user.last_name) |
                                                    Q(type='message', doctor=user.username))
    elif user.usertype == 'nurse':
        notifications = Notification.objects.filter(Q(type='appointment') |
                                                    Q(type='message', doctor=user.username))
    fullNotes = list(reversed(notes))

    return render(request, 'notifications.html', {'user': user, 'notifications': notes, 'notes': fullNotes})


def uploadpatient(request):
    if not request.user.is_authenticated() or request.user.person.usertype == 'patient':
        return redirect('/login/')

    user = request.user.person
    if request.method == 'POST':
        form = UploadPatientForm(request.POST, request.FILES)
        if form.is_valid():
            handle_upleaded_file(request.FILES['file'])

    notes = getNotifications(user)

    return render(request, 'uploadpatient.html', {'user': user, 'notifications': notes,
                                                  'form': UploadPatientForm})

def messages(request):
    if not request.user.is_authenticated():
        return redirect('/login/')

    user = request.user.person
    notes = getNotifications(user)
    people = None
    if user.usertype == 'patient':
        people = Person.objects.filter().exclude(usertype='patient')
    else:
        people = Person.objects.filter()

    messages = Message.objects.filter(Q(sender=user.username) | Q(receiver=user.username))

    return render(request, 'messages.html', {'user': user, 'notifications': notes, 'form': MessageForm,
                                             'people': people, 'messages': messages})

def sendmessage(request):
    if not request.user.is_authenticated():
        return redirect('/login/')

    user = request.user.person
    form = MessageForm(request.POST)
    if form.is_valid():
        cleanedData = form.cleaned_data
        recipient = cleanedData['receiver'].replace("(","").replace(")","").replace(":","").split()[2]
        today = time.strftime("%Y-%m-%d") + " " + time.strftime("%H:%M:%S")
        message = Message(sender=user.username, receiver=recipient, message=cleanedData['message'],
                          date=today)
        message.save()

        notification = Notification(type='message', date=today, user=user.username, doctor=recipient)
        notification.data2 = user.first_name + " " + user.last_name + " (" + user.username + ")"
        if user.usertype == 'doctor':
            notification.data2 = "Dr. " + user.last_name + " (" + user.username + ")"

        if len(str(cleanedData['message'])) >= 90:
            notification.data = cleanedData['message'][:90] + "..."
        else:
            notification.data = cleanedData['message']

        activity = Activity(data=user.username + " sent a message to " + recipient,
                            date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
        activity.save()
        notification.save()
        stats = SystemStats.objects.filter()[0]
        stats.messagesSent += 1
        stats.save()

    return redirect('/messages/')


def admitpatient(request, id):
    if not request.user.is_authenticated() or request.user.person.usertype == 'patient':
        return redirect('/login/')

    person = Person.objects.filter(usertype='patient', pk=id)[0]
    if not Person.objects.filter(status='Admitted').count()>199:
        person.status = 'Admitted'
        person.save()
        activity = Activity(data=request.user.person.username + " admitted " + person.username + " to the hospital",
                            date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
        activity.save()
        stats = SystemStats.objects.filter()[0]
        stats.patientsAdmitted += 1
        stats.save()

    return redirect('/userlist/')


def dischargepatient(request, id):
    if not request.user.is_authenticated() or request.user.person.usertype == 'patient':
        return redirect('/login/')

    person = Person.objects.filter(usertype='patient', pk=id)[0]
    person.status = 'Discharged'
    person.save()
    activity = Activity(data=request.user.person.username + " discharged " + person.username + " from the hospital",
                            date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
    activity.save()

    return redirect('/userlist/')


def adminpanel(request):
    if not request.user.is_authenticated() or request.user.person.usertype != 'admin':
        return redirect('/login/')
    log = Activity.objects.filter().order_by('-pk')
    return render(request, 'adminpanel.html', {'user': request.user.person, 'log': log})


def permissions(request):
    if not request.user.is_authenticated() or request.user.person.usertype != 'admin':
        return redirect('/login/')

    users = Person.objects.filter().exclude(usertype='admin')
    return render(request, 'permissions.html', {'user': request.user.person, 'users': users,
                                                'form': UpdateUsertypeForm})

def updateusertype(request, id):
    if not request.user.is_authenticated() or request.user.person.usertype != 'admin':
        return redirect('/login/')

    stats = SystemStats.objects.filter()[0]
    user = Person.objects.filter(pk=id)[0]
    if user.usertype == 'doctor':
        stats.totalDoctors -= 1
    elif user.usertype == 'nurse':
        stats.totalNurses -= 1
    elif user.usertype == 'patient':
        stats.totalPatients -= 1

    user.usertype = request.POST.get('usertype').lower()
    if user.usertype == 'admin':
        stats.totalAdmins += 1
    elif user.usertype == 'doctor':
        stats.totalDoctors += 1
    elif user.usertype == 'nurse':
        stats.totalNurses += 1
    elif user.usertype == 'patient':
        stats.totalPatients += 1

    user.save()
    activity = Activity(data=request.user.person.username + " changed the usertype of " + user.username + " to "
                             + request.POST.get('usertype').lower(),
                            date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
    activity.save()

    return redirect('/permissions/')

def systemstats(request):
    if not request.user.is_authenticated() or request.user.person.usertype != 'admin':
        return redirect('/login/')

    user = request.user.person
    stats = SystemStats.objects.filter()[0]
    totalUsers = stats.totalPatients + stats.totalNurses + stats.totalDoctors + stats.totalAdmins
    stats.notificationsReceived = Notification.objects.filter().count()
    stats.oldestUser = Person.objects.order_by('birthdate')[0].birthdate
    return render(request, 'systemstats.html', {'user': user, 'stats': stats, 'totalUsers': totalUsers})


def getNotifications(user):
    notes = []
    if user.usertype == 'patient':
        notes = Notification.objects.filter(Q(type='appointment', user=user.username) |
                                            Q(type='appointment', data2=(user.first_name + " " + user.last_name + " (" + user.username + ")")) |
                                            Q(type='message', doctor=user.username) |
                                            Q(type='prescription', user=(user.first_name + " " + user.last_name + " (" + user.username) + ")") |
                                            Q(type='medicalresult', user=user.username))
    elif user.usertype == 'doctor':
        notes = Notification.objects.filter(Q(type='appointment', doctor=user.last_name) |
                                            Q(type='message', doctor=user.username) |
                                            Q(type='medicaltest'))
    elif user.usertype == 'nurse':
        notes = Notification.objects.filter(Q(type='appointment') |
                                            Q(type='message', doctor=user.username))

    return list(reversed(notes))[:11]


# When database is wiped, create 6 doctor accounts and 7 nurse accounts.
def createData():

    doctors = ['Jablonsky', 'Rivera', 'Anderson', 'Reynolds', 'Walsh', 'Harrison']
    for i in range(1, 7):
        doctor_username = ("doctor" + str(i))
        user = User.objects.create_user(username=doctor_username, email=(doctors[i - 1].lower() + "@health.net"),
                                        password=doctor_username, first_name=doctors[i - 1], last_name=doctors[i - 1])
        user = auth.authenticate(username=doctor_username, password=doctor_username)
        user.save()
        person = Person(username=doctor_username, email=(doctors[i - 1].lower() + "@health.net"),
                        password=doctor_username, first_name="Person", last_name=doctors[i - 1],
                        person=user, phone=("585000000" + str(i)), birthdate='1973-11-04', usertype='doctor',
                        preferred_hospital='Strong Memorial Hospital', sex='Male', primary_physician='none',
                        last_physical='2014-11-11', health_history='none', status='none')
        if i > 3:
            person.preferred_hospital = 'Highland Hospital'
        person.save()
        print("Doctor #" + str(i) + " created!")

    nurses = ['Matilda', 'Joy', 'Jackie', 'Nightingale', 'Lincoln', 'Rached', 'Espinosa']
    for i in range(1, 8):
        nurse_username = ("nurse" + str(i))
        user = User.objects.create_user(username=nurse_username, email=(nurses[i - 1].lower() + "@health.net"),
                                        password=nurse_username, first_name=nurses[i - 1], last_name=nurses[i - 1])
        user.save()
        user = auth.authenticate(username=nurse_username, password=nurse_username)
        person = Person(username=nurse_username, email=(nurses[i - 1].lower() + "@health.net"),
                        password=nurse_username, first_name="Person", last_name=nurses[i - 1],
                        person=user, phone=("585000001" + str(i)), birthdate='1973-11-04', usertype='nurse',
                        preferred_hospital='Strong Memorial Hospital', sex='Female', primary_physician='none',
                        last_physical='2014-11-11', health_history='none', status='none')
        if i > 4:
            person.preferred_hospital='Highland Hospital'
        person.save()
        print("Nurse #" + str(i) + " created!")

    user = User.objects.create_user(username='zxcv', email='admin@health.net', password='zxcv', first_name='admin',
                                    last_name='none')
    user = auth.authenticate(username='zxcv', password='zxcv')
    user.save()
    person = Person(username='zxcv', password='zxcv', email='admin@health.net', first_name="Admin", last_name='none',
                    person=user, phone='0000000000', birthdate='1973-11-04', usertype='admin', preferred_hospital='none',
                    sex='none', primary_physician='none', last_physical='none', health_history='none', status='none')
    person.save()

    stats = SystemStats(totalAdmins=1, totalDoctors=6, totalNurses=7, totalPatients=0, successfulLogins=0,
                        failedLogins=0, appointmentsCreated=0, medicationsPrescribed=0, testsConducted=0,
                        messagesSent=0, notificationsReceived=0, patientsAdmitted=0, oldestUser='none')
    stats.save()

    return redirect('/login/')


def sendtext(request, number):
    from twilio.rest import TwilioRestClient
    if not request.user.is_authenticated():
        return redirect('/login/')

    user = request.user.person
    form = MessageForm(request.POST)
    if form.is_valid():
        cleanedData = form.cleaned_data
        account_sid = 'ACe212fa202fc8eda023a8103d97b9f7e4'
        auth_token = '84e58d6c5791812287efe0d8c9cea55c'
        client = TwilioRestClient(account_sid, auth_token)
        client.messages.create(to="+1" + number, from_='+16502156528', body=user.first_name + " " + user.last_name
                                                                            +": " + cleanedData['message'])
        recipient = cleanedData['receiver'].replace("(","").replace(")","").replace(":","").split()[2]
        today = time.strftime("%Y-%m-%d") + " " + time.strftime("%H:%M:%S")
        message = Message(sender=user.username, receiver=recipient, message=cleanedData['message'],
                          date=today)
        message.save()

        notification = Notification(type='message', date=today, user=user.username, doctor=recipient)
        notification.data2 = user.first_name + " " + user.last_name + " (" + user.username + ")"
        if user.usertype == 'doctor':
            notification.data2 = "Dr. " + user.last_name + " (" + user.username + ")"

        if len(str(cleanedData['message'])) >= 90:
            notification.data = cleanedData['message'][:90] + "..."
        else:
            notification.data = cleanedData['message']

        activity = Activity(data=user.username + " sent a message to " + recipient,
                            date=time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S"))
        activity.save()
        notification.save()
        stats = SystemStats.objects.filter()[0]
        stats.messagesSent += 1
        stats.save()


    return redirect('/messages/')