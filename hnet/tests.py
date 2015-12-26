from django.test import TestCase
from hnet.models import Person
from django.contrib.auth.models import User
from hnet.models import MedicalHistory
from hnet.models import Prescription
from hnet.models import handle_uploaded_file

#first, last, user, password, dob, email, phone
#class PersonTestCase(TestCase):
#    def setup(self):
#        Person.objects.create(firstname='michael', lastname='vincent', username='mvyo', email='yoyo@hotmail.com', dob='01/01/1900', phone='2058474243')
#        Person.objects.create(firstname='guy', lastname='pal', username='gpal', email='thispal@yahoo.com', dob='05/14/1991', phone='5082470125')
#        Person.objects.create(firstname='sir', lastname='man', username='mvyo', email='goodemail@gmail.com', dob='03/14/1996', phone='3849182483')

class UploadTestUserRegex(TestCase):

    def setup(self):
        line1 = self.Create_Test_PersonUser()
        line2 = self.Create_Test_History()
        line3 = self.Create_Test_Prescription()

    def Create_Test_PersonUser(self):
        user = User.objects.create_user(username='test-1', email='tyshingler@gmail.com',
                                        password='PASSWORD', first_name='Tyler',
                                        last_name='Shingler')
        user.save()
        person = Person(person=user, phone=6149479011,
                         birthdate='1995-03-12', first_name='Tyler',
                         last_name='Shingler', email='tyshingler@gmail.com',
                         username='test-1', usertype='patient', sex='Male',
                         preferred_hospital='H1')
        person.save()
        str = person.__str__()

        user.delete()
        person.delete()

        return str

    def Create_Test_History(self):
        med = MedicalHistory(patient='txs2025',
                              textHistory='History')
        med.save()
        str = med.__str__()
        med.delete()
        return str

    def Create_Test_Prescription(self):
        pre = Prescription(patient='txs2025',doctor='Doc1',drugname='drug1',
                               dosage='1',quantity='10',description='drugdesc',
                               instructions='Once per day')
        pre.save()
        str = pre.__str__()
        pre.delete()
        return str


    # line = "[Username,User,Name,11/11/2011,email,6149479011]"

    def Create_file_for_testing(self):
        user = User.objects.create_user(username='txs2025', email='tyshingler@gmail.com',
                                        password='PASSWORD', first_name='Tyler',
                                        last_name='Shingler')
        user.save()
        person = Person(person=user, phone=6149479011,
                         birthdate='1995-03-12', first_name='Tyler',
                         last_name='Shingler', email='tyshingler@gmail.com',
                         username='txs2025', usertype='patient', sex='Male',
                         preferred_hospital='H1')
        person.save()

        med = MedicalHistory(patient='txs2025',
                              textHistory='History')
        med.save()

        pre = ['']
        pre = Prescription(patient='txs2025', doctor='Doc1', drugname='drug1',
                               dosage='1', quantity='10', description='drugdesc',
                               instructions='Once per day')
        pre.save()

        filename = person.user_export()

        user.delete()
        person.delete()
        #med.delete()
        #pre.delete()

        return filename


    def test_import_user(self):
        line1 = self.Create_Test_PersonUser()
        self.assertEqual(Person.import_user(line=line1).__str__(), line1 + "\n")

    def test_import_History(self):
        line2 = self.Create_Test_History()
        self.assertEqual(MedicalHistory.import_History(line=line2).__str__(), line2 + "\n")

    def test_import_Prescription(self):
        line3 = self.Create_Test_Prescription()
        self.assertEqual(Prescription.import_Prescription(line=line3).__str__(), line3)

    def test_import_file(self):
        #Get file and pass to upload file
        conferm = handle_uploaded_file(filename=self.Create_file_for_testing())
        self.assertEqual(conferm, "yyy")