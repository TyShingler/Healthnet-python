from django.db import models
from django.contrib.auth.models import User
import re


class Person(models.Model):
    person = models.OneToOneField(User, related_name='person')
    first_name = models.CharField(max_length=25)
    last_name = models.CharField(max_length=25)
    username = models.CharField(max_length=25)
    password = models.CharField(max_length=32)
    birthdate = models.DateField()
    email = models.EmailField(max_length=48)
    phone = models.CharField(max_length=15, default=0)
    sex = models.CharField(max_length=15)
    preferred_hospital = models.CharField(max_length=50)
    usertype = models.CharField(max_length=8)
    primary_physician = models.CharField(max_length=50)
    last_physical = models.CharField(max_length=50)
    health_history = models.CharField(max_length=600)
    status = models.CharField(max_length=10)

    # CSV
    # before coma #:value
    def __str__(self):
        str = self.username                     # Username 0
        str += "," + self.first_name            # First Name 1
        str += "," + self.last_name             # Last Name 2
        str += "," + self.birthdate.__str__()   # Birthdate 3
        str += "," + self.sex                   # Sex 4
        str += "," + self.email                 # Email 5
        str += "," + self.phone.__str__()       # Phone 6
        str += "," + self.preferred_hospital    # Hospital 7
        str += "\n"
        return str

    def user_export_fileName(self):
        return self.username + "-export"

    def user_export(self):
        name = self.user_export_fileName()
        file = open(name, "w")
        str = self.__str__()
        str1 = MedicalHistory.export(username=self.username)
        str += str1
        str += Prescription.export(username=self.username)
        file = open(name, "w")
        file.write(str)
        file.close()

        return name

    @staticmethod
    def import_user(line):
        line_split = re.split('[,]', line)
        if User.objects.filter(username=line_split[0]) == None:
            raise Exception('There was a user with the same Username!!!')

        user = User.objects.create(username=line_split[0], email=line_split[5],
                                   password='PASSWORD', first_name=line_split[1],
                                   last_name=line_split[2])
        user.save()

        person = Person(person=user, phone=line_split[6],
                        birthdate=line_split[3], first_name=line_split[1],
                        last_name=line_split[2], email=line_split[5],
                        username=line_split[0], usertype='patient', sex=line_split[4],
                        preferred_hospital=line_split[7])
        person.save()

        return person


class Appointment(models.Model):
    doctor = models.CharField(max_length=20)
    date = models.DateTimeField()
    description = models.CharField(max_length=100)
    p_username = models.CharField(max_length=100)
    p_first_name = models.CharField(max_length=100)
    p_last_name = models.CharField(max_length=100)
    hospital = models.CharField(max_length=50)

    def export(self, username):
        return self.export_Appts()

    def export_Appts(self, username):
        appts = Appointment.objects.filter(p_username=username)
        str = ""
        for x in range(0,len(appts)):
            str += appts[x].__str__()
        str = "\n"



    def __str__(self):
        str = "{"
        str += self.doctor
        str += "," + self.p_first_name
        str += "," + self.p_last_name
        str += "," + self.p_username
        str += "," + self.description
        str += "," + self.date
        str += ""
        return str

class MedicalHistory(models.Model):
    patient = models.CharField(max_length=50)       #patient = username
    textHistory = models.CharField(max_length=500)

    def export(username):
        medicalHistory = MedicalHistory.objects.filter(patient=username)
        string = medicalHistory[0].__str__()
        return string

    def __str__(self):
        str = self.patient              # 0
        str += "," + self.textHistory   # 1
        str += "\n"
        return str

    def import_History(line):
        vars = re.split('[,]', line)
        med = MedicalHistory(patient=vars[0], textHistory=vars[1])
        med.save()
        return med




class Prescription(models.Model):
    doctor = models.CharField(max_length=50)
    patient = models.CharField(max_length=50)
    drugname = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    dosage = models.CharField(max_length=100)
    quantity = models.CharField(max_length=50)
    instructions = models.CharField(max_length=500)

    def export(username):
        perms = Prescription.objects.filter(patient=username)
        str = ""
        for x in range(len(perms)):
            str += perms[x].__str__()
        str += "\n"
        return str

    def __str__(self):
        str = "{"
        str += self.patient             #0
        str += "," + self.doctor        #1
        str += "," + self.drugname      #2
        str += "," + self.dosage        #3
        str += "," + self.quantity      #4
        str += "," + self.description   #5
        str += "," + self.instructions  #6
        str += ""
        return str

    def import_Prescription(line):
        string = ""
        vars = re.split("[{]", line)
        for x in range(1, len(vars)):
            vars[x] = re.split(",", vars[x])
            pre = Prescription(patient=vars[x][0], doctor=vars[x][1], drugname=vars[x][2],
                                   dosage=vars[x][3], quantity=vars[x][4], description=vars[x][5],
                                   instructions=vars[x][6])
            pre.save()
            string += pre.__str__()
        return string

class Notification(models.Model):
    type = models.CharField(max_length=50)
    date = models.CharField(max_length=100)
    user = models.CharField(max_length=50)
    doctor = models.CharField(max_length=50)
    data = models.CharField(max_length=200)
    data2 = models.CharField(max_length=200)

def handle_uploaded_file(filename):
    file = open(filename, 'r')
    lines = file.readlines()
    file.close()
    string = ""
    for x in range(0,len(lines)):
        line = lines[x]
        if(x == 0):
            string += "y"
            Person.import_user(line)
        elif(x == 1):
            string += "y"
            MedicalHistory.import_History(line)
        else:
            string += "y"
            Prescription.import_Prescription(line)
    return string

class Message(models.Model):
    sender = models.CharField(max_length=50)
    receiver = models.CharField(max_length=50)
    message = models.CharField(max_length=500)
    date = models.CharField(max_length=50)

class MedicalTest(models.Model):
    patient = models.CharField(max_length=50)
    testname = models.CharField(max_length=50)
    results = models.CharField(max_length=500)
    date = models.CharField(max_length=50)
    pending = models.CharField(max_length=10)

class Activity(models.Model):
    data = models.CharField(max_length=250)
    date = models.CharField(max_length=50)

class SystemStats(models.Model):
    totalAdmins = models.IntegerField()
    totalDoctors = models.IntegerField()
    totalNurses = models.IntegerField()
    totalPatients = models.IntegerField()
    successfulLogins = models.IntegerField()
    failedLogins = models.IntegerField()
    appointmentsCreated = models.IntegerField()
    medicationsPrescribed = models.IntegerField()
    testsConducted = models.IntegerField()
    messagesSent = models.IntegerField()
    notificationsReceived = models.IntegerField()
    patientsAdmitted = models.IntegerField()
    oldestUser = models.CharField(max_length=50)

    # averages