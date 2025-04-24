import pandas as pd
import keyboard, smtplib, subprocess, psutil, shutil
from glob import glob
from datetime import datetime
import sys, time, os, math, json
from tkinter import *
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# * Using .dlls and .NET assemblies
# * pip install pythonnet
# * See docs: https://pythonnet.github.io/pythonnet/python.html
import clr
from typing_extensions import Self

user = os.getlogin()
sys.path.append('C:/Users/%s/Dropbox/Instruments cloud/Robotics/Unchained BK/AS Scripts/API Scripts' % user)

class CustomAlert: # SMTP server alerts
    
    def __init__(self):
        self.when = 1 # 0 - always, 1 - only if there are problems
        self.server = "mailgateway.anl.gov"
        self.port = 25  # Common ports are 587 for TLS and 465 for SSL
        self.instrument = 'ICP-AARL200@anl.gov'
        self.to = "shkrob@anl.gov" # comma separated list
       
       
    def alert(self, subject="ALERT", body=None, importance=None):
        self.message = MIMEMultipart()
        self.message['From'] = self.instrument
        self.message['To'] = self.to
        self.message['Subject'] = subject

        if body:
            body_part = MIMEText(str(body), 'plain')  # 'plain' for plain text
            self.message.attach(body_part)
     
        if importance:
                self.message['Importance'] = importance

        try: 
            server = smtplib.SMTP(self.server, self.port)
            server.sendmail(self.instrument, self.to, self.message.as_string())
            server.quit()
        except Exception as e:
            print(">> Cannot send smtp e-mail, error = %s" % e)


class ICPInterface: #Interface for controlling a Perkins Elmer Syngistix ICP

    instrument_status = None
    plasma_status = None
    analysis_status = None
    analysis_sample = None
    autosampler_status = None
    client_status = []
    instrument_error = []
    connection_status = None

    # Initialize attributes and call the ICP interface

    def __init__(
        self,
        server_ip: str = "146.139.45.9",
        client_ip: str = "",
        name: str = "Normal run",
        dll_path: str = "C:/Program Files (x86)/PerkinElmer/Syngistix-ICP/SyngistixRemoteControl",
    ) -> Self:

        self.verbose = 1 # verbosity level
        self.user = os.getlogin() # user name
        self.smtp = CustomAlert() # mailer
        
        self.proc = None  # process pid for Syngistix GUI
        self.syn_client = None # Syngistix remote client
        self.dll = dll_path # dll path for remote Syngistix
        self.root = os.path.dirname(dll_path) # root directory for Syngistix binaries
        self.IP = server_ip # Syngistix remote server IP

        # container/rack attributes
        self.dir = "Z:/CONTAINERS" 
        self.exp_path = "Z:/RESULTS" 
        self.exp = None
        self.code = "Test" # container name
        self.container = "" # container json object
        self.samples = {} # json object with pedigree
        self.json = None # pathname for json file
        self.items = 90 # tubes in the rack
        self.columns = 15
        self.rows = 6

        # ICP attributes
        self.sample_info = "rack%d" % self.items
        self.methods = None # the list of ICP methods
        self.last_method = "WASH"
        self.last_dataset =  "Test"
        self.last_ID = self.last_dataset
        self.last_template = "MeansTemplate"

        # ICP analysis attributes
        self.done = 0 # samples done
        self.analyzed = [] # list of samples done
        self.start  = None # analysis start
        self.finish = None # analysis finish
        self.elements = [] # elements to analyze
        self.autosampler = {} # autosampler mappings
        self.Hg_on = False # Hg alignment
        self.rinse = 1 # number of rinse cycles
        self.unexpected = True # report "unexpected" samples
        self.decision = "Normal" # high level decision to the module
        self.keep = False # to keep plasma on after analysis
        self.last_error = None # last error
        self.last_warning = {} # last warning during analysis
        self.status = {} # json status record
        self.wash = False # if it is a wash cycle
        self.queue = [] # analsyis queue 
        self.calibrate = True # calibrate befor and after anal


        self.data_path="C:/Users/Public/PerkinElmer Syngistix/ICP/Data"

        if os.path.exists(self.data_path):
            print(">> Syngistix data folder found")
        else:
            print(">> Syngistix data folder %s missing, abort" % self.data_path)
            sys.exit(1)
        
        self.metals = {
                'Li': 3,    # Lithium
                'Na': 11,   # Sodium
                'K':  19,   # Potassium
                'Rb': 37,   # Rubidium
                'Cs': 55,   # Cesium
                'Be': 4,    # Beryllium
                'Mg': 12,   # Magnesium
                'Ca': 20,   # Calcium
                'Sr': 38,   # Strontium
                'Ba': 56,   # Barium
                'Sc': 21,   # Scandium
                'Ti': 22,   # Titanium
                'V':  23,   # Vanadium
                'Cr': 24,   # Chromium
                'Mn': 25,   # Manganese
                'Fe': 26,   # Iron
                'Co': 27,   # Cobalt
                'Ni': 28,   # Nickel
                'Cu': 29,   # Copper
                'Zn': 30,   # Zinc
                'Y':  39,   # Yttrium
                'Zr': 40,   # Zirconium
                'Nb': 41,   # Niobium
                'Mo': 42,   # Molybdenum
                'Ru': 44,   # Ruthenium
                'Rh': 45,   # Rhodium
                'Pd': 46,   # Palladium
                'Ag': 47,   # Silver
                'Cd': 48,   # Cadmium
                'Hf': 72,   # Hafnium
                'Ta': 73,   # Tantalum
                'W':  74,   # Tungsten
                'Re': 75,   # Rhenium
                'Os': 76,   # Osmium
                'Ir': 77,   # Iridium
                'Pt': 78,   # Platinum
                'Au': 79,   # Gold
                'Hg': 80,   # Mercury
                'La': 57,   # Lanthanum
                'Ce': 58,   # Cerium
                'Pr': 59,   # Praseodymium
                'Nd': 60,   # Neodymium
                'Pm': 61,   # Promethium
                'Sm': 62,   # Samarium
                'Eu': 63,   # Europium
                'Gd': 64,   # Gadolinium
                'Tb': 65,   # Terbium
                'Dy': 66,   # Dysprosium
                'Ho': 67,   # Holmium
                'Er': 68,   # Erbium
                'Tm': 69,   # Thulium
                'Yb': 70,   # Ytterbium
                'Lu': 71    # Lutetium
            }

        self.begin_session(name)

#=================================== json serialization =======================================

    def to_json(self):
        self.status = {
            "decision" : self.decision,             # high level decision sent to module
            "keep" : self.keep,                     # whether to keep plasma On after analysis
            "code": self.code,                      # last container code
            "container": self.container,            # last container to analyze
            "method": self.last_method,             # last method
            "dataset": self.last_dataset,           # last dataset
            "run ID" : self.last_ID,                # last run ID
            "template": self.last_template,         # last dataset template
            "last error" : self.last_error,         # last errors/warnings (Syngistix)
            "last warning" : self.last_warning,     # last warnings (this code)
            "done" : self.done,                     # how many samples were analyzed
            "start" : self.start,                   # start datetime stamp of the analysis
            "finish" : self.finish,                 # finish datetime stamp of the analysis
            "analyzed": self.analyzed,              # list of analyzed samples
            "autosampler queue" : self.queue,       # autosampler queue
            "autosampler map" : self.autosampler,   # autosampler full map
            "Hg on" : self.Hg_on,                   # do Hg lamp realignment 
            "rinse" : self.rinse,                   # how many rinses after analysis, can be zero
            "calibrate" : self.calibrate,           # do calibrations before and after
            "errors log" : self.instrument_error    # all instrument errors/warnings
        }

        self.update_json_log()

        return self.status

    def update_json_log(self):
        f = os.path.join(self.data_path,"Reports","ICP_%s.json" % self.last_ID)
        try: 
            with open(f, 'w') as g:
                json.dump(self.status, g, indent=4)
        except:
            print(" >> Cannot write ICP status file %s" % f)

    def from_json(self, j):
        self.status = j
        
        self.keep = j.get("keep", False)
        self.last_method = j.get("method", "WASH")
        self.last_dataset = j.get("dataset", "test")
        self.last_template = j.get("template", "MeansTemplate")
        self.Hg_on = j.get("Hg on", False)
        self.rinse = j.get("rinse", 1)
        self.calibrate = j.get("calibrate", False)

        self.instrument_error = []
        self.done = 0
        self.last_error = None
        self.last_warning = None
        self.analyzed = []
        self.queue = []
        self.autosampler = {}

        self.container = j.get("container", None)
        if self.container: 
            self.unpack_container(self.container)
            self.analyzed = j.get("analyzed", [])
            if self.analyzed:
                self.write_sampleinfo("",0)
                self.analyzed = []


#############################################  GUI handling ################################################

    def begin_session(self, name):
        if self.IP: 
            if self.run_syngistix():
                self.connect2syngistix(name)
                self.get_methods()
            else:
                print(">> GUI not running, cannot be reached")
        else: 
            print(">> No valid IP for Syngistix")

    def restart_syngistix(self):        
        try: 
            proc = self.is_syngistix()
            if proc:
                proc.terminate()
                proc.wait()
            self.begin_session("Recovery")
            self.run_wash(2)
            return 1
        except Exception as e: 
            print(">> Recovery failed with error code = %s" % e)
            return 0

    def is_syngistix(self):
        s = "Syngistix-ICP.exe"
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                #print(proc.info['name'])
                if s in proc.info['name']:
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        print(">> Syngistix GUI not running")
        return None

    def poll_GUI(self):
        for count in range(3): # polling
            try:
                print("--- GUI poll, attempt %d" % (count+1))  
                if self.is_syngistix():
                    print("--- GUI running")
                    return 1
                else: time.sleep(30)
            except Exception as e: 
                print("--- GUI poll error: %s" % e)
                return 0
        return 0

    def run_syngistix(self):
        s = os.path.join(self.root,"Syngistix-ICP.exe")

        for count in range(3): # three attempts to restart
            try: 
                self.proc = self.is_syngistix()
                if self.proc is None:
                    print("\n\n>> Attempt %d to (re)start Syngistix GUI" % (count+1))

                    self.proc = subprocess.Popen([s], 
                                 creationflags = subprocess.DETACHED_PROCESS,
                                 close_fds=True)

                    if self.poll_GUI(): 
                        time.sleep(60)
                        if self.is_syngistix(): 
                             return True                    
                else:
                    print(">> Syngistix GUI already running")
                    return True
            except Exception as e: 
                print(">> GUI error: %s" % e)

        print(">> Unable to launch GUI, abort")
        return False

    def crash_plasma_off(self):  # if GUI crashes, try to restart GUI, optional plasma off, data storing

        self.decision = "Socket error"

        try: 
            self.proc.terminate()
            time.sleep(5)
        except Exception as e:
            print(">> Crash recovery error: %s" % e)

        for count in range(3): # three attempts to recover
            print("\n\n ####### GUI recovery attempt %d #########\n\n" % (count+1))
            try: 
                if self.run_syngistix():
                    if self.connect2syngistix("Recovery run"):
                        #if not self.keep: self.plasma(False)   # plasma
                        self.plasma(False)   # always plasma off in the recovery mode                                   
                        self.save_results() # data
                        self.smtp.alert("Syngistix GUI recovered successfully") # alerting
                        break
            except Exception as e:
                print(">> Crash recovery error: %s" % e)
        
        self.smtp.alert("Failed to recover GUI and data", importance = "high")

######################################### Interface calls ##############################################

    # Call the ICP interface
    def connect2syngistix(self, name): # connect to Syngistix

        if os.path.exists(self.dll):
            print(">> Syngistix API folder found")
        else:
            print(">> Syngistix API folder %s missing, abort" % self.dll)
            return 0
        
        sys.path.append(self.dll)
        clr.AddReference("RemoteSyngsitix")

        import RemoteSyngistix
        
        if self.verbose:
            print(">> Loaded Syngistix API assembly and modules for ICP control")

        try: 
            self.RemoteSyngistix = RemoteSyngistix
            self.syn_client = RemoteSyngistix.SyngistixInterface()
        
            if self.verbose:
                print(">> Initiated client, checking status callbacks")
        
            self.syn_client.connectionStatusCallback = (
                RemoteSyngistix.ConnectionStatusCallback(self.connection_status_callback)
                )
        
            self.syn_client.statusCallback = RemoteSyngistix.StatusCallback(
                self.status_callback
                )
        
            self.syn_client.plasmaStatusCallback = RemoteSyngistix.PlasmaStatusCallback(
                self.plasma_status_callback
                )
        
            self.syn_client.analysisStatusCallback = RemoteSyngistix.AnalysisStatusCallback(
                self.analysis_status_callback
                )
        
            self.syn_client.analysisSampleCallback = RemoteSyngistix.AnalysisSampleCallback(
                self.analysis_sample_callback
                )
        
            self.syn_client.instrumentStatusCallback = (
                RemoteSyngistix.InstrumentStatusCallback(self.instrument_status_callback)
                )
        
            self.syn_client.autosamplerStatusCallback = (
                RemoteSyngistix.AutosamplerStatusCallback(self.autosampler_status_callback)
                )
        
            self.syn_client.errorCallback = RemoteSyngistix.ErrorCallback(
                self.error_callback
                )
       
            s = self.syn_client.Connect(clientIP=self.IP, 
                                        serverIP=self.IP, 
                                        name=name)
            if not s: 
                self.smtp.alert("No connection to Syngistixs")
                self.syn_client = None

            if self.verbose: 
                print("\n\n>> ICP connection completed: %s" % s)
                print(">> Session name = %s\n\n" % name)                
            
            return True

        except:
            self.syn_client = None
            return False

    def __del__(self): # Disconnect from the ICP interface
        if self.syn_client:
            self.syn_client.Disconnect()
            if self.verbose:
                print(">> ICP disconnected")


        
####################################### status callback #####################################################################

    def status_callback(self, status: str): # Callback function for status"
        self.client_status.append(status)

    def error_callback(self, num: int, msg: str, severity: int): # Callback function for errors
        dt = datetime.now()
        s = datetime.strftime(dt, "%m-%d-%Y %H:%M:%S")

        self.instrument_error.append({"timestamp" : s, 
                                      "severity": severity, 
                                      "message": msg})

    def errors_after(self):
        self.last_error = []
        good = datetime.strftime(self.last_good_poll, "%m-%d-%Y %H:%M:%S")

        if self.verbose == 2:
            print("+++ Checks errors/warnings after %s" % good)
            print("+++ %s" % self.instrument_error)

        if self.instrument_error:
            for e in self.instrument_error:
                dt = datetime.strptime(e["timestamp"], "%m-%d-%Y %H:%M:%S")
                if dt>self.last_good_poll:
                    self.last_error.append(e)

        if self.last_error: 
            print(pd.DataFrame(self.last_error))

        return len(self.last_error)

    def analysis_status_callback(self, status: int): # Callback function for analysis status

        self.analysis_status = status
           
        if self.verbose:
            print(">> Analysis status = %s" % self.analysis_status)

    def analysis_sample_callback(self, sampleID: str): # Callback function for analysis sample
        if ':' in sampleID:
            self.analysis_sample = sampleID.split(":")[1].strip()
            if self.verbose:
                dt = datetime.now()
                s = dt.strftime("%m-%d-%Y %H:%M:%S")
                print("\n++++++++++ %s :: %s  ++++++++++\n" % (s, self.analysis_sample))
        else: 
            self.analysis_sample = None

    def plasma_status_callback(self, status: int): # Callback function for plasma status
        if status == 0:
            self.plasma_status = f"{status}: Plasma is On"
        elif status == 1:
            self.plasma_status = f"{status}: Plasma is Off"
        elif status == 2:
            self.plasma_status = f"{status}: Plasma Igniting"
        elif status == 3:
            self.plasma_status = f"{status}: Plasma Extinguishing"
        else:
            self.plasma_status = ""
            
        if self.verbose:
            print(">> Plasma status = %s" % self.plasma_status)

    def instrument_status_callback(self, status: int): #Callback function for instrument status
        self.instrument_status = (
            f"{status}: {self.RemoteSyngistix.InstrumentStatus(status).ToString()}"
        )
        
        if self.verbose:
            print(">> Instrument status = %s" % self.instrument_status)

    def autosampler_status_callback(self, status: int): #Callback function for autosampler status"""
        self.autosampler_status = (
            f"{status}: {self.RemoteSyngistix.InstrumentStatus(status).ToString()}"
        )
        
        if self.verbose:
            print("--- Autosampler status = %s" % self.autosampler_status)

    def connection_status_callback(self, status: int): #Callback function for connection status
        self.connection_status = status == 1
        
####################################### ICP auto analysis #######################################################

    def start_auto_analysis(
        self,
        method_name: str,
        dataset_name: str,
        sample_info_name: str,
        export_template_name: str,
        wavelength_realign: int = 0,
        precalibrate: bool = False,
        use_active_method: int = 0,
        ):
        # Start an auto analysis

        if not self.in_methods():
            print(">> Method does not exist, abort")
            return 0

        self.reset_sequence()

        if not self.wash: # regular analysis
            if  not self.plasma(True): 
                if self.verbose:
                    print(">> Cannot analyze, no plasma\n")
                return 0
        else:
            if self.verbose:
                print(">> No plasma check in a wash cycle\n")

        if ".xptx" not in  export_template_name:
             export_template_name+=".xptx" 

        if ".sifx" not in sample_info_name:
            sample_info_name += ".sifx"

        self.last_method = method_name 
        self.last_dataset =   dataset_name
        self.last_template = export_template_name
        self.sample_info = sample_info_name

        print("\n>> Method = %s" % self.last_method)
        print(">> DataSet = %s" % self.last_dataset)
        print(">> Sample Info = %s" % self.sample_info)
        print(">> Export Template = %s\n" % self.last_template)
        
        if precalibrate:
            self.syn_client.AutoAnalyzeAll(
                method_name,
                dataset_name,
                sample_info_name,
                export_template_name,
                wavelength_realign,
                use_active_method,
            )
        else:
            self.syn_client.AutoAnalyzeSamples(
                method_name,
                dataset_name,
                sample_info_name,
                export_template_name,
                wavelength_realign,
            )
        return 1

    def manual_sample(self, ID): # this is to run rinse manually to update sample info after <F2> stopping
                                 # by default goes into position 1 (rinse station)
        try:
            self.syn_client.ManualAnalyzeSample(ID)
            print("\n>> Manual run of %s began\n" % ID)
            self.wait_analysis()
            return 1
        except: 
            return 0
     
    def stop(self, message, opt=1):  # soft stop: part of regular analysis polling
                                     # opt=1 manual rinse, opt=0 reset
        self.finish = self.stamp()
        self.last_warning.update({ self.finish : message })

        if message: 
            self.smtp.alert("Stopped analysis, %s" % message)
            print("\n>> %s => Stop immediately !" % message)
        else: 
            self.smtp.alert("Stopped analysis")
            print("\n>> Stop immediately !")

        try:
            self.syn_client.StopAnalysis()
            self.wait_analysis()
            if opt: # manual rinse to reset
                print(">> Manual rinse to reset sample info")
                self.manual_sample("rinse0")
            else:  # reset sequence
                self.reset_sequence() 
            self.decision = "Soft stop"
            return 1
        except:
            self.decision = "Hard stop"
            return 0

    def hard_stop(self, message): # hard stop to terminate all activities, save files and plasma Off
        print(" >> Hard stop sequence activated")
        try: 
            self.stop(message)
            self.plasma(False)
            self.save_results()
            return 1
        except:
            return 0

    
    def ICP_ready(self): # checks Ready from the instrument, not too useful
                         # unfortunately returns Ready even during warming up
        self.decision = "Not Ready"
        if self.syn_client:
            try: 
                self.syn_client.GetInstrumentStatus()
                self.decision = self.syn_client.Response()
                print(">> Instrument status = %s" % self.decision)
                if self.decision == "Ready":
                    return 1
                else:
                    return 0
            except:
                return 0
        return 0

    def get_methods(self):
        self.methods = []
        try: 
            self.syn_client.GetMethodsList("")
            s = self.syn_client.Response().split("\t")
            print("\n\n>> Method list:")
            i=1
            for m in s:
                method = m.strip()
                if method: 
                    print("(%d) %s" % (i,method))
                    self.methods.append(method)
                    i+=1
            return self.methods
        except:
            print(">> Cannot load methods")
            return None

    def in_methods(self):
        if self.methods:
            self.get_methods()
        return self.last_method in self.methods

    def reset_sequence(self): # reset sequence to the beginning
        self.syn_client.ResetAnalysisSequence()
        if self.verbose:
            print(">> Reset sequence")
            print(">> Reset response = %s" % self.syn_client.Response())

    def Hg_realign(self):
        try: 
            if self.Hg_on:
                self.syn_client.HgRealign()
                print(">> start Hg lamp realign")
                print(">> Hg lamp response = %s" % self.syn_client.Response())
                return 1
        except:
            return 0

    def plasma_state(self):
        try:
            self.syn_client.GetPlasmaStatus()
            return self.syn_client.Response()
        except: 
            return "Instrument is off line"

    def plasma(self, state: bool = True):
        if not self.syn_client:
            return 0
        count=0
        mcount=5 # five attempts
        #pre-check
        status = self.plasma_state()
        if self.verbose:
           print("\n>> Plasma status: %s" % status)

        if state:
            if status == "On": 
            	if self.verbose:
                    print("\n>> Plasma is already on, no action")
                    return 1

            while True: 
                count+=1
                self.syn_client.PlasmaOn()
                status=self.syn_client.Response()
                if self.verbose:
                    print("\n>> Attempt %d of %d to turn plasma on, 2 min wait" % (count,mcount))
                time.sleep(120) # 2 minute wait
                # checking
                if self.plasma_status and "On" not in self.plasma_status:
                    print("\n>> Failed attempt %d of %d to turn plasma on" % (count,mcount))
                    if count==mcount: 
                        print("\n>> Cannot ignite plasma after %d repeated attempts, abort" % mcount)
                        self.smtp.alert("Plasma failed to ignite")
                        return 0
                else:
                    if self.verbose:
                        print("\n>> Plasma is on, stable")
                    return 1
        else:
            if status != "Off":
                while True:
                    count+=1
                    self.syn_client.PlasmaOff()
                    status=self.syn_client.Response()
                    if self.verbose:
                        print("\n>> Attempt %d of %d to turn plasma off, 30 s wait" % (count,mcount))
                    time.sleep(30)
                    if self.plasma_status and "Off" not in self.plasma_status:
                         print("\n>> Failed attempt %d of %d to turn plasma off" % (count,mcount))
                         if count==mcount: 
                            print("\n>> Cannot turn plasma off after %d repeated attempts, abort" % mcount)
                            self.smtp.alert("Plasma Off failed, attend immediately",importance = "high")
                            return 0
                    else:
                       if self.verbose:
                            print("\n>> Plasma is off")
                       return 1
        return 1

    def export(self, dataset: str, template: str):

        if ".xptx" not in template:
            template += ".xptx"

        f = os.path.join(self.data_path, "Designs", template)

        if os.path.exists(f):
            print(">> Found template %s" % template)
        else:
            print(">> Cannot find export template %s" % f)

        if self.syn_client: 
            try:
                self.syn_client.Export(dataset, template)
                status = self.syn_client.Response()
                print(">> Export status %s for dataset %s with template %s" % (status, dataset, template))
            except:
                print(">> Cannot export dataset")
        else:
            print(">> Cannot connect to Syngistix")


    def load_samples(self, name:str = None):
        if self.syn_client:
            if not name:
                name= self.sample_info
            if ".sifx" not in name:
                name += ".sifx"
            try: 
                f = os.path.join(self.data_path,"Sample Information", name)
                if os.path.exists(f): 
                    print("\n>> Found sample info file %s" % f)
                self.syn_client.DownloadSampleInfoFile(f)
                status = self.syn_client.Response()
                print("\n>> Status %s for loading sample info\n" % status)
            except:
                print(">> Unable to load sample info file\n")
   
    def sample2tube(self, 
                    i: int, 
                    size:int = 90): # 60 or 90 tube rack wells

        if size==90: cols=15
        if size==60: cols=12
        rows = int(size/cols)
        row = math.floor(i/cols)
        col = i - cols*row
        row = rows - row
        col = cols - col
        return "%s%d" % (chr(row+64),col)


    def write_sampleinfo(self, 
                         batch: str = "test", 
                         size: int = 90, # if zero use container information, last tube to sample
                         start: int = 0, # start offset
                         ): 

        if len(batch)==0: 
            mode = 0
            batch = self.code
            description = "generated from a container"
            if size==0: size=self.items
            size = min(size, self.items) 
        else: 
            mode = 1
            description = "generated by a user"
            self.items = size
            self.analyzed = []
            self.kind = ""

        s=os.path.join(self.data_path,"Sample Information")
        if os.path.exists(s):
            if self.verbose:
                print("\n>> Syngistix Sample Information folder found")
        else:
            print("\n>> Syngistix Sample Information folder %s missing, abort" % s)
            sys.exit(1)

        r = "rack%d.sifx" % self.items
        if self.verbose: 
            print(">> SampleInfo file %s generated" % r)

        n = 5 + self.items + self.rinse 

        with open(os.path.join(s,r), "w") as file:
            file.write("[System Description]\n")
            file.write("Description=%s\n" % description)
            file.write("MaxNoOfSamples=%d\n" % n)
            file.write("[Constant Parameters]\n")
            file.write("BatchID=%s\n" % batch)
            file.write("VolumeUnits=Vol,mL,0.001,,\n")
            file.write("WeightUnits=Wt,g,1.00,,\n")
            file.write("[User Defined List]\n")
            file.write("NumberOfUserDefined=2\n")
            file.write("UserDefined1=kind\n")
            file.write("UserDefined2=method\n")
            file.write("UserDefined3=\n")
            file.write("UserDefined4=\n")
            file.write("UserDefined5=\n")
            file.write("[Variable Parameter List]\n")
            file.write("NumberOfParameters=5\n")
            file.write("Parameter1=SampleNo\n")
            file.write("Parameter2=AutosamplerLocation\n")
            file.write("Parameter3=SampleID\n")    
            file.write("Parameter4=UserDefField1\n")
            file.write("Parameter5=UserDefField2\n")
            file.write("[Variable Parameter Data]\n")
            file.write("NumberOfDataValues=%d\n" % n)

            j=0 
            m=1 # item counter
            d=0 # data counter
            self.queue = []

            # important: sample wetting, home
            file.write("ValveWet=1,0,rinse,%s,%s\n" % (self.kind, self.last_method))

            if mode==0 and self.calibrate: 
                cal = "%s-%s-Cal" % (self.code, self.who)
                file.write("CalStart=2,1,calibrate,%s,%s\n" % (self.kind, self.last_method)) # well 1
                m+=1

            if mode: 
                self.autosampler = {}
                for i in range(self.items): 
                    if i>= start:
                        j = self.sample2tube(i, size)
                        label = "%s-%s" % (batch, j)
                        self.queue.append(label)
                        self.autosampler[i] = "%d,sample" % j
                        file.write("Data%d=%d,%d,%s,sample,%s\n" % (d+1, m+1, i+11, 
                                             label, self.last_method))
                        
                        m+=1
                        d+=1

            else: 
                for i, label in self.autosampler.items():
                    if j>=start and j<size:
                        s = label.split(',')[0]
                        if s not in self.analyzed:
                            self.queue.append(s)
                            file.write("Data%d=%d,%d,%s,%s\n" % (d+1, m+1, i+10, 
                                                          label, self.last_method))
                            m+=1
                            d+=1
                    j+=1

            if mode==0 and self.calibrate: 
                file.write("CalEnd=%d,1,calibrate,%s,%s,\n" % (m+1, self.kind, self.last_method)) # well 1
                m+=1

            if self.rinse: # optional extra rinse at the end of a sequence, home
                for i in range(self.rinse):
                    self.queue.append("rinse")
                    file.write("Rinse%d=%d,0,rinse,%s,%s\n" % (i+1, m+1, self.kind, self.last_method))
                    m+=1
    
            file.close()
            self.sample_info = "rack%d" % self.items
            self.load_samples()

########################################### containers ##################################################################

    def load_json(self, name: str):
        self.container = None
        self.code = None
        self.json = os.path.join(self.dir, "Container_%s.json" % name)
        try:
            with open(self.json, 'r') as f:
                self.container = json.load(f)
                self.code = self.container["code"]
        except:
            print(">> no container input for %s" % self.json)
            
            
    def write_json(self, name: str = "default"):
        self.json = os.path.join(self.dir, "Container_%s.json" % self.code)
        with open(self.json, 'w') as f:
            json.dump(self.container, f, indent=4)
            
    def stamp(self):
        now = datetime.now()
        stamp = now.strftime('%Y%m%d_%H%M%S')
        return stamp

    def unpack_container(self, 
                         name: str, 
                         sort: bool = False): # sort autosampler record in the normal autosampler order (right nearmost)

        self.load_json(name)
        return self.unpack_self_container(sort)

    def unpack_self_container(self, 
                              sort: bool = False): 
    # sort autosampler record in the normal autosampler order (right nearmost)
                        

        if not self.container: 
            return 0

        self.autosampler={}
        self.elements = []

        self.code = self.container["code"]

        dt = datetime.now() 
        self.last_ID ="%s_%s" % (self.code, dt.strftime("%H%M"))
        self.last_dataset = "run_%s" % self.last_ID

        self.rack = self.container["rack"]
        self.route = self.container["route"]
        self.creator = self.container["creator"]
        self.samples = self.creator["content"]
        self.who = self.creator["location"]
        
        self.items = self.rack["items"]
        self.rows = self.rack["rows"]
        self.cols = self.rack["columns"]

        if self.verbose:
            print("\n>> Unpacking container %s" % self.code)
            print(">> Created %s by %s" % (self.creator["datetime"], self.who))
            print(">> %dx%d rack of %d tubes" % (self.rows, self.cols, self.items))

        for ID in self.samples:

            # original well designations
            self.kind = self.samples[ID]["type"]
            well = ID.split(":")[-1] # creater well
            
            # elemental composition
            es=list(self.samples[ID]["constitution"])
            s = ", ".join(es)
            for e in es:
                if e not in self.elements:
                    self.elements.append(e)

            # ICP rack and autosampler designations
            if self.who == "BK":
                row =  ord(well[0]) - ord('A') + 1
                col = int(well[1:]) 
                row_ = self.rows + 1 - row 
                col_ = self.cols + 1 - col
                index = col_ + (row-1)*self.cols
                well_ = well

            if self.who == "PAL1":
                index = int(well) # assumes PAL indexing direction=2 (Y axis)
                row = 1 + math.floor((index-1)/self.cols)
                col = index - (row-1)* self.cols
                row_ = 1 + math.floor((index-1)/self.rows)
                col_ = index - (row_-1)* self.rows
                well_ = "%s%d" % (chr(64+row), col) # PAL1 labels

            tube = "%s%d" % (chr(64+row_), col_)
            
            self.autosampler[index] = "%s-%s-%s,%s" % (self.code, self.who, well_, self.kind)

            if self.verbose:
                print("%s %s -> ICP %s: sample %d (%s) :: %s" % (self.who, well, tube, index, self.kind, s))

        # create sample info file
        if sort: 
            self.autosampler = dict(sorted(self.autosampler.items()))
        
        self.write_sampleinfo("",0)

        # create the ordered list of elements for analysis
        self.elements = sorted(self.elements, key=lambda x: self.metals[x])
        if self.verbose:
                s = ", ".join(self.elements)
                print("\n>> Elements to analyze: %s\n" % s)

        return 1

###################################### polling #########################################################

    def is_report(self, name):
        if ".csv" not in name:
            name += ".csv"

        r = os.path.join(self.data_path,"Reports", name)
        if not os.path.exists(r):
            print(">> No exported file found, exporting %s" % name)
            self.export(name, self.last_template)
            if not os.path.exists(r): 
                if self.verbose:
                    print(">> No report file for %s" % name)
                return None
        return r

    def count_completed(self): # count reported samples
        r = self.is_report(self.last_dataset)
        if r:
            df = pd.read_csv(r)
            return df['Sample ID'].nunique()
        return 0

    def convert_report(self, name): # convert report to a better readable format
        views = ["radial", "axial"]

        if not name:
            name = self.last_dataset

        r = self.is_report(name)
        if r:
            df = pd.read_csv(r)
            if 'View' not in df.columns:
                df['View'] = 1
            df.rename(columns={"User Value 1": "kind"},   inplace=True)
            df.rename(columns={"User Value 2": "method"}, inplace=True)

            sample_IDs = df['Sample ID'].unique().tolist()  
            elements = sorted(df['Elem'].unique().tolist(), 
                              key=lambda x: self.metals[x])
            qs = []

            for ID in sample_IDs:
                subset = df[df['Sample ID'] == ID]
                q = { "Sample": ID, "kind" : "sample", "method" : "", "Date": "", "Time": ""}

                for e in elements:
                    q["radial_%s" % e] = math.nan
                    q["axial_%s" % e] = math.nan
                    for _, row in subset.iterrows():  # logs the last measurement for each sample ID and element
                        if row["Elem"] == e:
                            i=int(row["View"])
                            u="%s_%s" % (views[i], e)
                            q[u] = row["Int (Corr)"]
                            q["Date"] = row["Date"].replace("/","-")
                            t = datetime.strptime(row["Time"], "%I:%M:%S %p")
                            q["Time"] =  t.strftime("%H:%M:%S")

                            if "method" in row: 
                                q["method"] = row["method"].strip()
                                
                            if "kind" in row: 
                                q["kind"] = row["kind"].strip()
                                
                            
                if "rinse" not in q["kind"] and "WASH" not in q["method"]:
                    qs.append(q)

            if qs: 
                out = pd.DataFrame(qs)
                out = out.dropna(axis=1, how='all')
                r = r.replace(".csv", "_converted.csv")
                out.to_csv(r, index=False)
                if self.verbose:
                    print(">> Converted report %s\n" % name)
            else:
                if self.verbose:
                    print(">> No data of interest to convert\n")

    def check_run_completion(self): # check completion of report after analysis
        flag=0 
        self.done = self.count_completed()

        if self.done<self.items:
             flag+=1
             if self.verbose:
                print(">> Incomplete analysis: %d samples out of %d" % (self.done, self.items))

        e = self.errors_after()
        if e: flag+=1

        return flag  # returns 1 if analysis is incomplete and 2 if it is both incomplete and there is error

###########################################################################################

    def find_exp(self): # find experiment with the container
        for s in os.listdir(self.exp_path):
            sp = os.path.join(self.exp_path, s)
            if os.path.isdir(sp):
                for f in os.listdir(sp):
                    if self.code in f:
                        return sp
        return self.exp_path

    def copy2exp(self, exp: str = None): # copy ICP result and status files to experiment
         r = os.path.join(self.data_path,"Reports","*%s*.*" % self.code)
         files = glob(r)
         if exp:
             self.exp = exp
         else:
             self.exp = self.find_exp()
         if os.path.exists(self.exp): 
            print("\n>> Found experiment folder %s" % self.exp)
            for f in files:
                s = os.path.basename(f)
                if not f.endswith('.csvx'): 
                    print("---> copied file %s" % s)
                    shutil.copy(f, self.exp)
                if f.endswith('.csv') and "converted" not in f:
                    g = f.replace(".csv","_converted.csv")
                    if g not in files:
                        self.convert_report(s)
                        if os.path.exists(g):
                            shutil.copy(g, self.exp)
                            print("---> copied file %s" % os.path.basename(g))
                    
            return 1
         else:
             return 0

    def save_results(self, opt=1): # save json and log records and (optionally) results
        self.to_json()        
        self.log_record()
        if self.done>1 and opt: 
            self.export(self.last_dataset, self.last_template)
            self.convert_report("")
            self.copy2exp(self.exp)
        
    def log_record(self):
        f = os.path.join(self.data_path,"Reports\ICP_log.csv")
        try:
            if os.path.exists(f): 
                out = open(f, 'a')
            else:
                out = open(f, 'w')
                out.write("timestamp,analyzed,termination,method,template")

            out.write("\n%s,%s,%s,%s,%s" % (self.stamp(), 
                                                self.last_dataset,
                                                self.decision, 
                                                self.last_method, 
                                                self.last_template))
            out.close()
            if self.verbose:
                print(">> Updated dataset reports log file")
        except:
            print(">> Cannot update dataset reports log file")

    def check_user_cancel(self):
        for e in self.last_error:
            if "User canceled analysis" in e["message"]:
                return 1
        return 0

    def poll_once(self):
        self.last_poll = datetime.now()
        self.last_stamp = self.stamp()
        return self.analysis_status, self.analysis_sample

    def poll_continuously(self, mode:int = 0): #1 when resume

        last_flag=-1
        self.analysis_status = -1
        stop=0
        self.unexpected = True # report "unexpected" samples
        self.last_sample = ""
        self.last_error = None
        self.last_warning = {}
        dt = datetime.now()
        self.start = self.stamp()
        self.finish = None
        self.last_good_poll = dt

        if mode==0: 
            self.done = 0
            self.analyzed = []
        else: 
            if self.analyzed: 
                self.last_sample = self.analyzed[-1]

        time.sleep(5)

        while True:

            flag, s = self.poll_once()

            if flag==0 and last_flag==1: # Idle
                break

            if flag==2: # Paused
                print(">> Waiting to resume, press <Analyze Sample> button in GUI")

            if self.errors_after():
                if  self.check_user_cancel: # <F8> pause pressed
                    self.last_good_poll = self.last_poll
                else: # all other errors
                    self.smtp.alert("Errors/warnings during analysis", 
                                    body = self.last_error)
                    if self.is_syngistix(): flag=5 # hard stop
                    else: flag=4
                    
            else:
                self.last_good_poll = self.last_poll

            if flag == 4:  # incorrect response 
                self.last_warning.update({ self.last_stamp : s })
                print("\n>> %s, stop immediately" % s)
                self.smtp.alert("Syngistix communication fault during analysis", body=s)
                break

            if keyboard.is_pressed('F2'):  # Check if the F2 key is pressed
                stop = self.stop("F2 pressed")
                flag = 3 # soft stop
                break

            status = self.plasma_state()

            if not self.wash and "Off" in status:
                w = "Plasma is off, stop immediately"
                self.last_warning.update({ self.last_stamp : w })
                print("\n>> %s, stop immediately\n" % w)
                self.smtp.alert("Plasma off during regular analysis")
                flag = 5 # hard stop
                break

            if flag==1: # analysis in progress, count and log sample
                if s and s != self.last_sample:
                    sexp = self.queue[self.done]
                    if s != sexp and self.unexpected:
                        print(">> ALERT: unexpected sample in analysis queue!")
                        print(">> Processing %s, expected %s in queue" % (s, sexp))
                    self.done+=1
                    self.analyzed.append(s)
                    self.last_sample = s
            
            last_flag = flag
            time.sleep(10) 

        self.finish = self.stamp()

        if flag==3 or flag==5: # soft or hard stops
            if stop == 0:
                print("\n\n!!! Stopping analysis, exporting data, and turning plasma off !!!\n")
                self.syn_client.StopAnalysis()
                flag = 5 # hard stop
                self.decision = "Hard stop"                
            else:
                self.decision = "Soft stop"
            self.plasma(False)

        if flag==4: # lost connection to Syngistix
            self.crash_plasma_off() # attempt recovery
        else: # all other cases
            self.save_results()

        if self.done < len(self.queue):
            return 0, flag

        return 1, flag  # 1 if analysis is incomplete; 0 - complete 
                # flag is 0 is Idle, 1 if not, 3 if error or F2 stopping - soft stop, 4 if socket error
                # 5 is hard stop means do not try to use robotic arm, autosampler can be damaged

    def run_wash(self, times=1):  # special run for washing the lines that can be run at the end
         self.last_method = "WASH"
         self.last_template = "MeansTemplate"
         self.last_dataset =  "Wash_%s" % self.stamp()      
         self.sample_info = "wash%d" % times
         self.wash = True

         if self.start_auto_analysis(self.last_method,
                                      self.last_dataset, 
                                      self.sample_info, 
                                      self.last_template):
             self.wait_analysis()


    def wait_analysis(self):
        time.sleep(5)
        while self.analysis_status == 1:
            time.sleep(5)

    def wait_idle(self):
        time.sleep(5)
        while self.analysis_status != 0:
            time.sleep(5)

    def run_analysis(self):
        
        self.Hg_realign()
        self.wash = "WASH" in self.last_method
        self.decision = "Normal"
        self.last_error = None
        self.last_warning = None

        if self.syn_client:
            if self.start_auto_analysis(self.last_method,
                                      self.last_dataset, 
                                      self.sample_info, 
                                      self.last_template):

                status, flag = self.poll_continuously()

                if flag == 4:
                    self.decision = "Socket error"
                    self.save_results(0)
                    return 4

                if flag == 3:
                    self.decision = "Soft stop"
                    self.smtp.alert("Soft stop, plasma off")
                    self.plasma(False)
                    self.save_results()
                    return 3

                if flag == 5:
                    self.decision = "Hard stop"
                    self.smtp.alert("Hard stop, plasma off")
                    self.plasma(False)
                    self.save_results()
                    if self.restart_syngistix():
                        self.status["decision"] = "Hard stop, recovered"
                        self.update_json_log()
                        return 6
                    return 5

                if status==0: 
                    self.decision = "Incomplete"

                if not self.keep:
                    self.plasma(False)

                self.save_results()

                if status==1: 
                    return 1
                else: return 2

            else:
                print(">> Cannot analyze, abort")
                self.decision = "Failed"
                self.smtp.alert("Failed, plasma off")
                self.save_results()
                self.plasma(False)
                return 7
        else:
            self.decision = "No connection"
            print(">> No connection to Syngistixs, abort")
            return 0



############################################ tests #################################################################

    def test_plasma(self):
        self.plasma(True)
        time.sleep(30)
        self.plasma(False)

    def test_simple(self):
         self.last_method = "Food Dye v3"
         self.last_template = "MeansTemplate"
         self.last_dataset =  "Test_%s" % self.stamp()      
         self.write_sampleinfo("test", 90) # batch ID and the number of sample tubes in a rack
         return self.run_analysis()


    def container_simple(self, name):
         self.last_method = "Food Dye v3" # 
         self.last_template = "MeansTemplate"
         self.last_dataset = "run_%s" % name
         self.unpack_container(name)
         sys.exit(0)
         if not self.container: return 0
         self.write_sampleinfo("", 90, start=30) # 30 tubes with offset
         # self.write_sampleinfo("") # full rack
         return self.run_analysis() 

    def restart_from_status_file(self, f):
        try: 
            with open(f, 'r') as q:
                self.status = json.load(q)
                self.from_json(self.status)
                return self.run_analysis() 
        except:
            print(">> Cannot find status file %s, abort" % f)
            return 0


#############################################################################################################


if __name__ == "__main__":
    # * Example usage

    icp = ICPInterface("146.139.45.9", "", "Normal run")  
    icp.code = "31X14"  # six samples

    #icp.export("Test", "MeansTemplate.xptx")

    #icp.run_wash()

    icp.container_simple(icp.code) 

    #icp.test_simple()

    #icp.resume_and_poll()

    #icp.convert_report(dataset)  

    #icp.manual_sample()

    icp.copy2exp()
