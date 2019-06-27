'''
Created on 2019年6月6日

@author: WangBowen
20190611:更新到V0.2，修正学习一门课程后的掉线问题，以及状态不更新为”完成“的问题
20190612：更新到V0.3，修正一些小的bug及文字提示
'''
import sys
import re
import requests
import datetime
import random
import time
from bs4 import BeautifulSoup 
from PyQt5.QtCore import pyqtSignal,QThread
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit, 
    QTextEdit, QGridLayout, QApplication, QPushButton)
from PyQt5.QtGui import QIcon

class FormGridLayout(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        self.usr = QLabel('用户名：')
        self.pwd = QLabel('密码：')
        self.log = QLabel('日志')
        self.bt1 = QPushButton('登录')
        self.bt1.clicked.connect(self.tryLogin)
        self.bt2 = QPushButton('自动学习')
        self.bt2.clicked.connect(self.autoLearn)

        self.usrEdit = QLineEdit()
        self.pwdEdit = QLineEdit()
        self.logEdit = QTextEdit()

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(self.usr, 1, 0)
        grid.addWidget(self.usrEdit, 1, 1)
        grid.addWidget(self.pwd, 1, 2)
        grid.addWidget(self.pwdEdit, 1, 3)
        
        grid.addWidget(self.bt1, 2, 1)
        grid.addWidget(self.bt2, 2, 3)

        grid.addWidget(self.log, 3, 0)
        grid.addWidget(self.logEdit, 3, 1, 5, 3)

        self.setLayout(grid) 

        self.setGeometry(300, 300, 450, 350)
        self.setWindowTitle('安徽专技继教在线--学习辅助系统V0.3--作者：wbw')  
        self.setWindowIcon(QIcon('bw.png'))  
        self.show()
        self.bt2.setDisabled(True)
        
        global browser,headers
        browser = requests.session()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'}
        
        
    def appendLog(self, str1):
        self.logEdit.append(str1)
        if(str1 == '学习结束，请到http://www.zjzx.ah.cn进行考试~'):
            self.bt2.setDisabled(False)
        QApplication.processEvents()
        
    #登录系统
    def tryLogin(self):
        self.logEdit.append("----------开始登录----------")
        self.bt1.setDisabled(True)
        self.logEdit.append("用户名："+self.usrEdit.text()+"，密码："+self.pwdEdit.text())
        if(self.usrEdit.text().strip() == ''):
            self.appendLog("----------登录失败，用户名不能为空----------")
            self.bt1.setDisabled(False)
            return
        if(self.pwdEdit.text().strip() == ''):
            self.appendLog("----------登录失败，密码不能为空----------")
            self.bt1.setDisabled(False)
            return
        url = 'http://www.zjzx.ah.cn/passport/ilogin?service=http://www.zjzx.ah.cn/auth_check'
        #从网站先获取lt等状态位
        resp = browser.get(url, headers = headers).content.decode('utf-8')
        soup = BeautifulSoup(resp,'html.parser')
        lt = soup.find(attrs={'name':'lt'})['value']
        form = {
        'username':self.usrEdit.text().strip(),
        'lt':lt,
        '_eventId':'submit',
        'password':self.pwdEdit.text().strip(),
        'submit':'登录'
        }
        #开始执行登录，成功则获取用户姓名
        url = 'http://www.zjzx.ah.cn/passport/ilogin?service=http://www.zjzx.ah.cn/auth_check'#登录地址
        resp = browser.post(url, headers = headers,data=form)
        url = 'http://www.zjzx.ah.cn/index.action'
        resp = browser.get(url, headers = headers).content.decode('utf-8')
        xm = re.search('(?<=欢迎你，).*?(?=！<a)', resp)
        if xm is not None:
            self.appendLog("----------登录成功，姓名：%s----------"%(xm.group(0)))
            self.bt2.setDisabled(False)
            self.usrEdit.setDisabled(True)
            self.pwdEdit.setDisabled(True)
        else:
            self.appendLog("----------登录失败，请核对信息后重试----------")
            print(resp)
            self.bt1.setDisabled(False)
            return
     
    #开始自动学习课程
    def autoLearn(self):
        self.bt2.setDisabled(True)
        self.learnThread = LearnThread()
        self.learnThread.trigger.connect(self.appendLog)
        self.learnThread.start()
    
    
class Course:
    def __init__(self, name, url, curTime, totalTime, captureList):
        self.name = name
        self.url = url
        self.curTime = curTime
        self.totalTime = totalTime
        self.captureList = captureList
        
class Capture:
    def __init__(self, name, url, lTime):
        self.name = name
        self.url = url
        self.lTime = lTime
        
# 增加了一个继承自QThread类的类，重新写了它的run()函数
# run()函数即是新线程需要执行的：执行一个循环；发送计算完成的信号。
class LearnThread(QThread):
    trigger = pyqtSignal(str)
    def __init__(self):
        super().__init__()
    def run(self):
        self.trigger.emit("\r----------获取课程列表----------")
        url = 'http://www.zjzx.ah.cn/user/portal!programscourseall.action'
        resp = browser.get(url, headers = headers).content.decode('utf-8')
        soup = BeautifulSoup(resp,'html.parser')
        tab_list = soup.findAll('table', class_='tabcleck')
        course_list = []
        for tab in tab_list:
            tr_list = tab.findAll('tr')
            for tr in tr_list:
                if len(tr.findAll('a')) == 0 :#排除table表头
                    continue
                if re.search('未完成',str(tr)) is None:
                    continue
                td_list = tr.findAll('td')
                #因为无法获取单个视频的总时长，故用总课时减去已学时间，作为本次学习时间
                learnTime = int((int(re.search('\d*?(?=分钟)',str(td_list[3])).group(0))) - (int(re.search('\d*?(?=.0分钟)',str(td_list[2])).group(0))))
                if(learnTime < 0):#可能会出现未及时更新、未考试的情况，跳过此课程
                    continue
                #开始获取课程的各章节信息
                self.trigger.emit(td_list[0].find('strong').text + '——————')
                resp = browser.get('http://www.zjzx.ah.cn'+td_list[0].findAll('a')[1]['href'], headers = headers)
                soup = BeautifulSoup(resp.content.decode('utf-8'),'html.parser')
                a_list = soup.findAll('a', href=re.compile('\/lms\/learning\/courseware'))
                captureList = []
                for a in a_list:
                    lTime = int(learnTime/len(a_list))*60 + random.randint(70,150)#把总学习时长平均到每节课中，并随机多学习一段时间
                    self.trigger.emit('    '+a.find('span',class_='class_title_text').text)
                    captureList.append(Capture(a.find('span',class_='class_title_text').text, a['href'], lTime))
                course_list.append(Course(td_list[0].find('strong').text, 'http://www.zjzx.ah.cn'+td_list[0].findAll('a')[1]['href'], re.search('\d*?(?=.0分钟)',str(td_list[2])).group(0), re.search('\d*?(?=分钟)',str(td_list[3])).group(0),captureList))
        self.trigger.emit("\r----------开始自动学习所有课程----------")
        # 循环学习所有课程
        for course in course_list:
            self.trigger.emit("课程:%s，总课时为%s分钟，目前已学习%s分钟----------" %(course.name,course.totalTime,course.curTime))
            #循环学习课程的每个章节
            for capture in course.captureList:
                print("学习章节:%s，本次学习%s秒, 预计于%s结束" %(capture.name, capture.lTime, datetime.datetime.strftime(datetime.datetime.now()+datetime.timedelta(seconds=capture.lTime),'%H:%M:%S')))
                self.trigger.emit("开始学习章节:%s，本次学习%s秒, 预计于%s结束" %(capture.name, capture.lTime, datetime.datetime.strftime(datetime.datetime.now()+datetime.timedelta(seconds=capture.lTime),'%H:%M:%S')))
                resp = browser.get('http://www.zjzx.ah.cn'+capture.url, headers=headers).content.decode('utf-8')#打开视频学习页面
                userId = re.search('(?<= id=\"userId\" value=\").*?(?=\")', resp).group(0)
                studyId = re.search('(?<=studyId\:\').*?(?=\'\})', resp).group(0)
                save_url = 'http://www.zjzx.ah.cn' + re.search('\/lms\/learning\/save.*?(?=\')', resp).group(0)
                rand_num = random.randint(111,999)
                init_url = 'http://www.zjzx.ah.cn/lms/learning/init/' + studyId + '_' + str(rand_num)
                check_url = 'http://www.zjzx.ah.cn/lms/learning/check/' + studyId + '_' + str(rand_num)
                check_form = {'userId' : userId}
                save_form = {'lastPage' : '0'}
                resp = browser.post(init_url, headers=headers, data=check_form)#给网站一个初始的状态位
                for i in range(1,capture.lTime):
                    if i%15 == 0:#每15秒更新一次在线状态
                        #self.trigger.emit("更新在线状态......")
                        print("更新在线状态......")
                        resp = browser.post(check_url, headers=headers, data=check_form)
                        print(resp.content.decode('utf-8'))
                    if i%60 == 0:#每60秒提交一次学习进度
                        #self.trigger.emit("提交学习进度......")
                        print("提交学习进度......")
                        resp = browser.post(save_url, headers=headers, data=save_form)
                        print(resp.content.decode('utf-8'))
#                     if i%300 == 0:#长时间学习后会掉线，每5分钟请求一次页面，防止掉线
#                         url = 'http://www.zjzx.ah.cn/user/portal!programscourseall.action'
#                         resp = browser.get(url, headers = headers)
#                         print(resp.status_code)
                    time.sleep(1)
                time.sleep(3)#每次学习后休息3秒
                self.trigger.emit('本次学习完成！')
            #学习完成一门课程后，刷新一下课程才会更新为 已完成
            url = 'http://www.zjzx.ah.cn/user/portal!programscourseall.action'
            resp = browser.get(url, headers = headers)
            time.sleep(3)#每次学习后休息3秒
        self.trigger.emit('学习结束，请到http://www.zjzx.ah.cn进行考试~')
        
        
if __name__ == '__main__':

    app = QApplication(sys.argv)
    ex = FormGridLayout()
    sys.exit(app.exec_())