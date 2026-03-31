'''
Created on Mar 28, 2015

@author: bustamac
Download and install Python module from

https://pythonhosted.org/PyDAQmx/
7-Feb-2024 converted to python 3 format
'''


import sys 
sys.path.append(r'C:\Program Files (x86)\IronPython 2.7\Lib')
#sys.path.append(r'C:\Python27\Lib\site-packages')
sys.path.append(r'C:\Program Files (x86)\Triangle MicroWorks\Protocol Test Harness\PythonScripts')

#from PyDAQmx import *          #iron python
import PyDAQmx           #python
import numpy as np
import matplotlib.pyplot as plt

#from PyDAQmx.DAQmxTypes import *
#from PyDAQmx.DAQmxConstants import *
#from PyDAQmx.DAQmxCallBack import *
#from PyDAQmx.DAQmxFunctions import *
#from PyDAQmx.DAQmxConfig import *

#print 'DAQlib', DAQlib

from math import *
import ctypes

from time import sleep 
from TimeFunctions import (getdatetime, getDeltaTime_ms) 

class DAQmx(object):
    def __init__(self, samp_per_chan=1080, sample_rate=64800.0):
        self.task_running = False
        self.numSampsPerChannel = samp_per_chan
        self.sampleRate = ctypes.c_double(sample_rate)

        self.nidaq = ctypes.windll.nicaiu
        self.NI_Devices()
               
    def NI_Devices(self):
        self.NI_devices = []
        buff = ctypes.create_string_buffer(2048)
        self.nidaq.DAQmxGetSysDevNames(ctypes.byref(buff), 2048)
        print ('hhh', buff, buff.value, type (buff.value), type (buff))
        print ('hhj', buff.value.decode(), type (buff.value.decode()))
        temp = [n.strip() for n in (buff.value.decode()).split(',') if n.strip()]
        #print 'NI-devices:', temp #self.NI_devices
        #print 'buff', buff
        #print 'buff.value', buff.value
        print('\nDAQmxGetSysDevNames-->', temp)
        
        for x in temp:
            device = ctypes.c_char_p(x.encode())
            #slot = ctypes.c_char_p(x)
            buff = ctypes.create_string_buffer(2048) 
            buff1 = ctypes.create_string_buffer(2048)
            buff2 = ctypes.create_string_buffer(2048)
            self.nidaq.DAQmxGetDevProductType(device, ctypes.byref(buff), 2048)
            #self.nidaq.DAQmxGetDevCompactDAQSlotNum(device, ctypes.byref(slot))
            self.nidaq.DAQmxGetDevTCPIPEthernetIP(device,ctypes.byref(buff1), 2048)
            self.nidaq.DAQmxGetDevTCPIPHostname(device, ctypes.byref(buff2), 2048)
            #print 'Device:%s ProductType:%s slot %i'  %(x,buff.value, slot)
            #print('Device:{0} ProductType:{1} slot: {2} IP address:{3} host:{4}'.format(x,buff.value, slot.value, buff1.value, buff2.value))
            self.NI_devices.append ([x,buff.value.decode()])
        
        print('class DAQmx NI_Devices self.NI_devices list:', self.NI_devices)
                
    def get_NI_Device(self):
        #return self.NI_devices
        return self.NI_devices

    def refresh_NI_Devices(self):
        self.NI_Devices()

          
    def generateSineWave(self,sysFrequencyX, sysFrequencyY, channels_to_modify, is_IR_chassis = False, **kwargs):
                
        print('\n<<starting generateSineWave >>>')
        include_noise= kwargs.get('include_noise')
        include_harmonics = kwargs.get('include_harmonics')
        noise_std = float(kwargs.get('noise_std'))
        highest_harm = int(kwargs.get('highest_harm'))
        SNR_db=float(kwargs.get('SNR_db'))


        sysFrequencyX = ctypes.c_double(sysFrequencyX)
        sysFrequencyY = ctypes.c_double(sysFrequencyY)

        phaseOffset = ctypes.c_double()
        temp1 = ctypes.c_double()
        temp2 = ctypes.c_double()

        elements_per_pole = 3
        X_index = 1
        
        #print 'type: self.samppleRate, self.numSampPerChannel', type(self.sampleRate), type(self.numSampsPerChannel)
        print('generateSineWave sysFrequencyX >',  sysFrequencyX, sysFrequencyX.value)
        print('generateSineWave sysFrequencyY >',  sysFrequencyY, sysFrequencyY.value)

        print('generateSineWave >>is_IR_chassis >>>', is_IR_chassis)

        print ('samples per cycle', self.sampleRate.value/sysFrequencyX.value)
        print ('self.sampleRate.value', self.sampleRate.value, type (self.sampleRate))
        #print 'self.is_IR_chassis', is_IR_chassis
        print ('number of channels', self.nChannels, type (self.nChannels))
        print ('self.numSampsPerChannel', self.numSampsPerChannel, type (self.numSampsPerChannel))

        #print 'number of samples self.sampleRate.value/sysFrequencyX.value = ', self.sampleRate.value/sysFrequencyX.value



        print('\n<<<< calculating data...\n')
        # Precompute angular steps per sample (loop-invariant)
        ang_step_x = 2.0 * pi / (self.sampleRate.value / sysFrequencyX.value)
        ang_step_y = 2.0 * pi / (self.sampleRate.value / sysFrequencyY.value)

        for i in range(self.nChannels):
            phaseOffset.value = self.phaseOffsets[i] * pi / 180.0
            base_offset = i * self.numSampsPerChannel

            for j in range(self.numSampsPerChannel):
                if is_IR_chassis:
                    Xelement = j % elements_per_pole

                    if Xelement == X_index:
                        temp1.value = self.dcOffsets[j] + self.amplitudes[j] * sin(
                            i * ang_step_y + phaseOffset.value)
                        temp2.value = self.calculateHarmonics(i, j, sysFrequencyY, phaseOffset)
                    else:
                        temp1.value = self.dcOffsets[j] + self.amplitudes[j] * sin(
                            i * ang_step_x + phaseOffset.value)
                        temp2.value = self.calculateHarmonics(i, j, sysFrequencyX, phaseOffset)
                else:
                    temp1.value = self.dcOffsets[i] + self.amplitudes[i] * sin(
                        j * ang_step_x + phaseOffset.value)
                    temp2.value = 0.0

                self.data[base_offset + j] = temp1.value + temp2.value


        self.writeDataToFile()

        self.datanp, self.time_points, self.all_sine_waves, self.all_sine_waves_no_harms = self.generateSineWaveNumPy(include_noise, include_harmonics, noise_std, channels_to_modify,
                                                                                                                      highest_harm, SNR_db)
        #print ('\nself.datanp generateSineWave', self.datanp, len (self.datanp), type (self.datanp))

        self.writeDataToFile("data_numpy_calc.txt",self.datanp)


        print('\n<<< sine wave generation complete >>>')
    
    def generateSineWaveNumPy(self, include_noise, include_harmonics, noise_std, channels_to_modify, highest_harm, SNR_db):

        print('\n<<< entering generateSineWaveNumPy \n')
        # Sine wave parameters

        fundamental_frequency = 60
        snr_db_empirical = 0

        # NI-DAQ parameters
        sampling_rate = self.sampleRate.value
        duration = float(self.numSampsPerChannel) / sampling_rate  # seconds
        num_of_channels = self.nChannels
        samps_per_chan = self.numSampsPerChannel

        all_sine_waves = []
        all_sine_waves_no_harms = []

        #channels_to_modify=[0,1,2,6,7,8]
        #channels_to_modify = [0,1,6,7]
        #noise_std= 0.2  # Original value = 0.3 standard deviation of the noise

        # Calculate the harmonic frequencies
        harmonics = np.arange(3,highest_harm + 1, 2) * fundamental_frequency

        print ('\n<<< sine_wave', type (sine_wave))
        # Calculate time points
        time_points = np.arange(0, duration, 1 / sampling_rate)
        #print ('time_points', len (time_points), time_points)

        # Print the harmonic frequencies
        print ('\nharmonics >>', harmonics)

        for i in harmonics:
            print(f"Harmonic {int(i / fundamental_frequency)}: {i} Hz")

        # Calculate sine wave values

        for j in range(num_of_channels):
            phase_offset = self.phaseOffsets[j] * pi / 180.0
            sine_wave = self.amplitudes[j] * np.sin(2 * np.pi * fundamental_frequency * time_points + phase_offset)
            #calculate harmonics
            if include_harmonics and j in channels_to_modify:
                temp = sine_wave + self.calculateHarmonics_np(phase_offset, time_points, highest_harm, fundamental_frequency)
            else:
                temp = sine_wave

            # Introduce noise
            #noise = 0.2 * np.random.normal(size=temp.shape)
            #print ("temp.shape. temp.size", temp.shape, temp.size)

            if include_noise and j in channels_to_modify:
                distorted_signal, snr_db_empirical = self.add_awgn_to_snr_db(temp, SNR_db)
            else:
                distorted_signal = temp

            print(f"snr_db_empirical: {snr_db_empirical:3.3f}")
            P_s=np.mean(temp**2)
            P_n_theoretical = noise_std**2
            snr_db_theoritical = 10*np.log10(P_s/P_n_theoretical)
            print (f"signal to noise theorical: {snr_db_theoritical:3.3f}")


            #temp = sine_wave
            #print ('\ncalling writeDataToFileNumPy')
            all_sine_waves.append (distorted_signal)
            all_sine_waves_no_harms.append(sine_wave)

        arr1 = np.concatenate (all_sine_waves, axis= None)

        self.writeDataToFileNumPy(time_points, arr1, samps_per_chan, all_sine_waves)

        return arr1, time_points, all_sine_waves, all_sine_waves_no_harms


    def add_awgn_to_snr_db(self, x, snr_db, rng=None):
        """
        Add zero-mean Gaussian noise to 'x' to achieve the target SNR in dB.
        Returns y (noisy) and the actual empirical SNR in dB.
        """
        print ("<<in add_awgn_to_snr_db method>>", type (x))
        if rng is None:
            rng = np.random.default_rng()
        P_s = np.mean(np.asarray(x) ** 2)
        sigma2 = P_s / (10 ** (snr_db / 10))
        sigma = np.sqrt(sigma2)
        noise = rng.normal(loc=0.0, scale=sigma, size=x.shape)
        y = x + noise
        # empirical SNR for this draw
        P_n = np.mean(noise ** 2)
        snr_db_empirical = 10 * np.log10(P_s / P_n)
        return y, snr_db_empirical

    def calculateHarmonics(self, i, j, sysFrequencyX, phaseOffset):
        '''
            Calculates harmonic components
            Use the same harmonics magnitude for all harmonic components
        '''
        result = 0.0

        if self.nthHarmonics:
            ang_step = 2.0 * pi / (self.sampleRate.value / sysFrequencyX.value)
            for n in range(len(self.nthHarmonics)):
                result += self.dcOffsets[j] + self.nthHarmonicsAmp[j] * sin(
                    i * self.nthHarmonics[n] * ang_step + phaseOffset.value)

        return result

    def calculateHarmonics_np(self, phaseOffset, time_points,highest_harm, fundamental_frequency):
        # Define the fundamental frequency (Hz)
        #fundamental_frequency = 60  #Hz

        # Define the number of harmonics to calculate
        #num_harmonics = 9

        # Calculate the harmonic frequencies
        harmonics = np.arange(1,highest_harm + 1, 2) * fundamental_frequency

        # Print the harmonic frequencies
        #print ('harmonics >>\n', harmonics)
        #print("Harmonic Frequencies:")
        #for i in harmonics:
        #    print(f"Harmonic %i: %i Hz"% (i / fundamental_frequency, i))

        # Create the harmonic waves (with reduced amplitudes)
        harmonic_waves = []
        for i, harmonic in enumerate(harmonics[1:]):
            #print("Calculating harmonics >> i, harmonic, harmonics", i, harmonic, harmonics)
            harmonic_amplitude = 1.0 / (i + 2)  # Reduce amplitude for higher harmonics
            harmonic_wave = harmonic_amplitude * np.sin(2 * np.pi * harmonic * time_points + phaseOffset)
            #print ('harmonic_wave', harmonic_wave, len(harmonic_wave))
            print(f"Calculating harmonics index i >> {i} , harmonics {harmonic/fundamental_frequency}, harmonic_amplitude {harmonic_amplitude:3.3f}")
            harmonic_waves.append(harmonic_wave)

        return sum(harmonic_waves)

    def fast_fourier_transform(self, no_subplot = True):
        sample_rate = self.sampleRate.value

        wave_form = self.datanp[:self.numSampsPerChannel]
        #print ('wave form >> ', wave_form)

        fft_output = np.fft.fft(wave_form, norm = "forward") #/ self.numSampsPerChannel
        #print ('fft_output', fft_output)
        frequencies = np.fft.fftfreq(len(wave_form), 1/sample_rate)

        # Plot the magnitude spectrum
        if no_subplot:
            plt.plot(frequencies[:len(frequencies) // 2], np.abs(fft_output)[:len(fft_output) // 2])
            plt.xlabel("Frequency (Hz)")
            plt.ylabel("Magnitude")
            plt.title("Frequency Spectrum of the Signal")
            plt.grid(True)
            plt.show()

        return fft_output, frequencies

    def plot_graphs (self, no_v_chans,no_i_chans, no_switches = 2):

        x_label_rotation = 0
        no_phases = 3
        #no_switches = 1
        switch_id = {0:'Sw1', 1:'Sw2'}
        phase_id = {0:'Phase A', 1: 'Phase B', 2: 'Phase C'}

        #fix, ax = plt.subplots()
        #fix.set_size_inches(12,8)

        num_samples = int (self.sampleRate.value / 60) - 1  #one cycle
        x = self.time_points[:num_samples]

        fig,axs = plt.subplots(2, 3, sharex=True, sharey=True)

        for switch in range (no_switches):
            for phase in range (no_phases):
                switch_offset = switch*no_phases
                v_chan_index = switch_offset + phase
                #voltage channels
                #axs[switch,phase].plot(x,self.all_sine_waves_no_harms[switch_offset+phase][:num_samples], label='Vclean', color = 'green')
                axs[switch,phase].plot(x,self.all_sine_waves[switch_offset+phase][:num_samples], label='V inj', color = 'orange')

                #current channels
                #print('current channel index', (v_chan_index + no_v_chans))
                if (v_chan_index + no_v_chans) < (no_v_chans + no_i_chans):
                    #axs[switch, phase].plot(x, self.all_sine_waves_no_harms[v_chan_index + no_v_chans][
                    #                           :num_samples], label='Iclean', color ='blue')
                    axs[switch, phase].plot(x, self.all_sine_waves[v_chan_index + no_v_chans][:num_samples],
                                            label='I inj', color ='red')

                #graph
                axs[switch,phase].grid()
                axs[switch,phase].set_title ('{0} {1}'.format (switch_id[switch], phase_id[phase]))
                print ('{0} {1}'.format (switch_id[switch], phase_id[phase]))

            #add x and y labels for subplots
            for ax in axs.flat:
                ax.set(xlabel="Time (s)", ylabel="Amplitude (V)")
                #ax.legend()

            handles, labels = ax.get_legend_handles_labels()
            fig.legend(handles, labels, loc='upper right')

            #fig.legend(loc='outside right upper')

            # Hide x labels and tick labels for top plots and y ticks for right plots.
            for ax in axs.flat:
                ax.label_outer()



        fig.suptitle('Voltage and current injection waveforms')

        plt.tight_layout ()
        plt.show()

    def subplots(self, Vchan,Ichan, fft_output, frequencies):

        x_label_rotation = 0
        fix, ax = plt.subplots(1,2)
        fix.set_size_inches(10, 6)

        num_samples = int(self.sampleRate.value / 60) - 1  # one cycle

        plt.subplot(1, 2, 1)
        plt.plot(frequencies[:len(frequencies) // 2], np.abs(fft_output)[:len(fft_output) // 2])
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Magnitude")
        plt.title("Frequency Spectrum of the Sine Wave")
        plt.grid(True)
        plt.xticks(rotation=x_label_rotation)

        plt.subplot(1, 2, 2)
        # Plot the sine wave
        plt.plot(self.time_points[:num_samples], self.all_sine_waves_no_harms[Vchan][:num_samples], label='V1')
        plt.plot(self.time_points[:num_samples], self.all_sine_waves[Vchan][:num_samples], label='V1 harm')
        plt.plot(self.time_points[:num_samples], self.all_sine_waves_no_harms[Ichan][:num_samples], label='I1')
        plt.plot(self.time_points[:num_samples], self.all_sine_waves[Ichan][:num_samples], label='I1 harm')

        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude (V)")
        plt.title("Sine Wave")
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=x_label_rotation)

        plt.tight_layout()
        plt.show()

    def writeDataToFile(self, fileName="calculated_wavefom_values.txt", arg=None):
        print('<<entering writeDataToFile method\n')
        fileName = "c:\\temp\\" + fileName

        data_to_write = self.data if arg is None else arg

        with open(fileName, 'w') as f:
            f.write('len(data_to_write %i)\n' % (len(data_to_write)))

            for index in range(len(data_to_write)):
                f.write('index %i, channel %i,sample %i, value %f\n' % (
                    index, index // self.numSampsPerChannel,
                    index % self.numSampsPerChannel, data_to_write[index]))

        print('<<end writeDataToFile method\n')
    

    def writeDataToFileNumPy(self, time_points, entire_array, samps_per_chan, all_sine_waves,
                             fileName="waveforms_numPy_array.txt"):

        print('\n<<entering writeDataToFileNumPy method\n')
        fileName = "c:\\temp\\" + fileName

        with open(fileName, 'w') as f:
            for index in range(len(entire_array)):
                f.write('index <%i>, channel > %i,sample > %i, value > %f\n' % (
                    index, index // samps_per_chan, index % samps_per_chan, entire_array[index]))

            f.write('~' * 40 + '\n')

            for sample in range(samps_per_chan):
                parts = ['%f' % wf[sample] for wf in all_sine_waves]
                f.write('index %i > %s\n' % (sample, ','.join(parts)))

        print('<<end  writeDataToFileNumPy method\n')


    def listNI_DAQ_devices(self):
        
        for x in self.NI_devices:
            
            #print 'x', x, type (x)
            device, ProductType = x 
            
            print('Device:%s ProductType:%s' %(device, ProductType))
            
    def setPhysChanName(self,name):
        #self.physChan.value  = name 
        self.physChan  =ctypes.c_char_p(name)        
        print('updated phys channel>', self.physChan)
        
    def getPhysChans(self):
        '''
        Returns a list of physical channels based on NI hardware detected
        '''
        new_list = []
        phys_chans =[]
        NI_dev = self.NI_devices
            
        #using list comprehension
        unique_matches = list (set(m for index in NI_dev for m in re.findall('cDAQ[\d]+', index[0] ))) 
        #print 'unique_matches', unique_matches, type (unique_matches)
        unique_matches.sort()
               
        for j in unique_matches:
            sub_list = []
            for k in range (len(NI_dev)):
                if j in NI_dev[k][0]:
                    sub_list.append(NI_dev[k][0])
            new_list.append(sub_list)                    
   
        
        for module in new_list:
            print('NI module:', module)
            try:
                phys_chans.append ('%s/ao0:2,%s/ao0:2,%s/ao0:5' %(module[1], module[2], module[3]))
                
            except IndexError:
                pass
                                 
        print('\nclass DAQmx getPhysChans method returning ** new_list', new_list)
        print('\n class DAQmx getPhysChans method returning ** phys_chans', phys_chans)
        #return phys_chans
        return new_list   
        
      
    def configure(self):
        '''
        Configure NI DAQ method
        configures data buffering if enabled
        '''              
        
        print('\n<<<in configure method...')
        time_string, self.start_time = getdatetime('local', True) 
        print('\n<<<%s>> starting configure task' %(time_string))
        #self.taskHandle = ctypes.c_void_p()

        #self.taskHandle = #PyDAQmx.TaskHandle()
        #self.nidaq.DAQmxCreateTask("", self.taskHandle)

        self.taskHandle = ctypes.c_void_p()

        ChanName = ctypes.c_char_p()
        minVal = ctypes.c_double (-10)
        maxVal = ctypes.c_double (10)
        taskName = ctypes.c_char_p()
        sampsPerChan = ctypes.c_int32(self.numSampsPerChannel)  # c_longlong(self.numSampsPerChannel)
        self.bytesWritten = 0
        sampsPerChanWritten = ctypes.c_int32()

        print('\ntype taskHandle>>>', type(self.taskHandle), self.taskHandle.value, ctypes.addressof(self.taskHandle))
        print('self.nidaq', self.nidaq)
        print('sampsPerChan', sampsPerChan.value)
        print('self.sampleRate', self.sampleRate, type (self.sampleRate))
        print('self.physChan ==>', self.physChan)

        print ('channel name', ChanName, ChanName.value)
        print ('check', type (self.physChan), self.physChan.value, type (self.physChan.value))
        print ('self.data >>', self.data, type (self.data))
        print ('taskName >>>', taskName, type(taskName))
        print ('self.data',self.data, type (self.data))

        #inferred_int_array = np.array([1, 2, 3])
        c_double_array = np.ctypeslib.as_ctypes(self.datanp)
        print ('\n<< >> ', type(c_double_array))



        # using PyDAQ methods
        #task = PyDAQmx.Task()
        #taskHandle = self.nidaq.TaskHandle()
        #print ( '\ntype task >>>', type (task), task.value)
        #print ('\TaskHandle >>>', TaskHandle)

        #for i in range (self.nChannels * self.numSampsPerChannel):
        #    self.data[i] = 2
         #   #print ('self.data', self.data[i])

        _chassis = self.physChan.value.decode().split('Mod')[0]
        print(f"DAQmxResetDevice chassis: {_chassis}")
        print(f"DAQmxResetDevice result:{self.errorCheck(self.nidaq.DAQmxResetDevice(ctypes.c_char_p(_chassis.encode())), 'DAQmxResetDevice')}")
        self._wait_for_device_ready(_chassis)

        print(f"DAQmxCreateTask result: {self.errorCheck(self.nidaq.DAQmxCreateTask(ChanName.value, ctypes.byref(self.taskHandle)), 'DAQmxCreateTask')}")

        #print('DAQmxResetDevice', self.nidaq.DAQmxResetDevice(self.physChan))

        print(f"DAQmxCreateAOVoltageChan result: {self.errorCheck(self.nidaq.DAQmxCreateAOVoltageChan(self.taskHandle, self.physChan.value, ChanName.value, minVal, maxVal, PyDAQmx.DAQmx_Val_Volts, None), 'DAQmxCreateAOVoltageChan')}")

        print(f"DAQmxSetWriteRegenMode result: {self.errorCheck(self.nidaq.DAQmxSetWriteRegenMode(self.taskHandle, PyDAQmx.DAQmx_Val_AllowRegen), 'DAQmxSetWriteRegenMode')}")

        print(f"DAQmxCfgSampClkTiming result: {self.errorCheck(self.nidaq.DAQmxCfgSampClkTiming(self.taskHandle, None, self.sampleRate, PyDAQmx.DAQmx_Val_Rising, PyDAQmx.DAQmx_Val_ContSamps, sampsPerChan), 'DAQmxCfgSampClkTiming')}")


        #c = self.nidaq.DAQmxStartTask(self.taskHandle)
        #print('print DAQmxStartTask >>>>', c)

        #self.nidaq.DAQmxRegisterDoneEvent(self.taskHandle, 0, DoneCallback, NULL


        #d = self.nidaq.DAQmxWriteAnalogF64(self.taskHandle, self.numSampsPerChannel, 0, 10, PyDAQmx.DAQmx_Val_GroupByChannel,
        #                               self.data,  None, None)


        print(f"DAQmxWriteAnalogF64 result: {self.errorCheck(self.nidaq.DAQmxWriteAnalogF64(self.taskHandle, sampsPerChan, False, 10, PyDAQmx.DAQmx_Val_GroupByChannel, c_double_array, ctypes.byref(sampsPerChanWritten), None), 'DAQmxWriteAnalogF64')}")
        #DAQmx_Val_GroupByScanNumber, DAQmx_Val_GroupByChannel

        self.bytesWritten += sampsPerChanWritten.value
        print ('%s OnEveryNSamplesEvent writing DAQ buffer: %i, total:%i ' %( time_string, sampsPerChanWritten.value, self.bytesWritten))


        #DAQmxWriteAnalogF64(taskHandle, SampsPerChannel,0,10.0,DAQmx_Val_GroupByChannel,data,NULL,NULL)
        # DAQmxWriteAnalogF64            (TaskHandle taskHandle, int32 numSampsPerChan, bool32 autoStart, float64 timeout, bool32 dataLayout,
        #                                       const float64 writeArray[], int32 *sampsPerChanWritten, bool32 *reserved);
        #DAQmxWriteAnalogF64(taskHandle, numSampsPerChannel,0,10.0,DAQmx_Val_GroupByChannel,data,NULL,NULL)
        # define DAQmx_Val_GroupByChannel                                          0   // Group by Channel
        # define DAQmx_Val_GroupByScanNumber                                       1   // Group by Scan Number


        print(f"DAQmxStartTask result: {self.errorCheck(self.nidaq.DAQmxStartTask(self.taskHandle), 'DAQmxStartTask')}")

                #task.StartTask()
        #task.DAQmxWriteAnalogF64(task, self.numSampsPerChannel, False, 10.0, DAQmx_Val_GroupByChannel,
        #                               callbackdata, byref(sampsPerChanWritten), None)
        #task.WriteAnalogScalarF64(1, 10.0, value, None)
        #task.StopTask()



        '''
        #self.errorCheck(self.nidaq.DAQmxCreateAOVoltageChan(self.taskHandle, self.physChan,'-', -10.0, 10.0,
        #                                                    DAQmx_Val_Volts, None), 'DAQmxCreateAOVoltageChan')
        self.nidaq.DAQmxCreateAOVoltageChan(self.taskHandle, self.physChan, b'', -10.0, 10.0,
                                                            PyDAQmx.DAQmx_Val_Volts, None)
        print('timing task')
        self.errorCheck(self.nidaq.DAQmxCfgSampClkTiming(self.taskHandle, "",self.sampleRate.value, DAQmx_Val_Rising,
                                                         DAQmx_Val_ContSamps, sampsPerChan), 'DAQmxCfgSampClkTiming')#1650
        self.bytesWritten = 0
        
        if self.dataBufferingEnabled:                
            
            id_some_data = create_callbackdata_id(self.data)      
                            
            everyNsamplesEventType = int32()
            
            def OnEveryNSamplesEvent_py (taskHandle, everyNsamplesEventType, nSamples, callbackData_ptr):
                sampsPerChanWritten = int32()
                callbackdata = get_callbackdata_from_id(callbackData_ptr)
                time_string, self.start_time = getdatetime('local', True)
                
                self.errorCheck (self.nidaq.DAQmxWriteAnalogF64(taskHandle, self.numSampsPerChannel, False, 10.0, DAQmx_Val_GroupByChannel, callbackdata,
                                                            byref (sampsPerChanWritten), None), 'DAQmxWriteAnalogF64')                      
            
                self.bytesWritten += sampsPerChanWritten.value
                #print '%s OnEveryNSamplesEvent writing DAQ buffer: %i, total:%i ' %( time_string, sampsPerChanWritten.value, self.bytesWritten)
                
                return 0
                
            def OnDoneEventCallBack_py (taskHandle, status, callbackData_ptr):
                            
                #callbackdata = get_callbackdata_from_id(callbackData_ptr)
                time_string, end_time = getdatetime('local', True) 
                print('\n<<%s>> OnDoneEventCallBack_py method...status (%i)' %(time_string, status))
                print('start time...', self.start_time)
                print('end_time', end_time)
                print('running time: %s'%( getDeltaTime_ms(self.start_time, end_time)))
            
                self.errorCheck(status, 'OnDoneEventCallBack_py')
            
                return 0
                       
            write_callback_prototype = CFUNCTYPE(int32, TaskHandle, int32, uInt32, c_void_p)        
            self.OnEveryNSamplesEventCallBack = write_callback_prototype(OnEveryNSamplesEvent_py)
            
            write_callback_prototype = CFUNCTYPE(int32, TaskHandle, int32, c_void_p)
            self.DoneCallback = write_callback_prototype(OnDoneEventCallBack_py)
            
            #OnDoneEventCallBack = DAQmxDoneEventCallbackPtr (self.OnDoneEventCallBack_py)
                            
            print('configuring voltage channel')
            print('self.physChan', self.physChan)
            print('DAQmx_Val_Volts', DAQmx_Val_Volts)
            print('self.sampleRate', self.sampleRate)
            print('self.numSampsPerChannel', self.numSampsPerChannel, type (self.numSampsPerChannel))
            print('selected device...')
                               
            #DAQmxSetWriteAttribute (genTaskHandle, DAQmx_Write_RegenMode, DAQmx_Val_DoNotAllowRegen)) DAQmx_Val_AllowRegen, DAQmx_Val_DoNotAllowRegen
            self.errorCheck(self.nidaq.DAQmxSetWriteAttribute (self.taskHandle, DAQmx_Write_RegenMode, DAQmx_Val_DoNotAllowRegen), 'DAQmxSetWriteAttribute')
            #// Register a callback on Every N Samples generated so that we can be trigged to refresh the output buffer.
            self.errorCheck (self.nidaq.DAQmxRegisterEveryNSamplesEvent (self.taskHandle, DAQmx_Val_Transferred_From_Buffer, self.numSampsPerChannel, 0, self.OnEveryNSamplesEventCallBack,  id_some_data), 'DAQmxRegisterEveryNSamplesEvent')
            #DAQmxRegisterDoneEvent(taskHandle,0,DoneCallback,NULL))
            self.errorCheck (self.nidaq.DAQmxRegisterDoneEvent (self.taskHandle, 0, self.DoneCallback, None), 'DAQmxRegisterDoneEvent')
            #// Double the size of the output buffer to provide enough sample at the generation start
            #// (usefull for high an update rate)
            self.errorCheck (self.nidaq.DAQmxSetAOUseOnlyOnBrdMem(self.taskHandle, self.physChan, 0), DAQmxSetAOUseOnlyOnBrdMem)
            self.errorCheck (self.nidaq.DAQmxSetAODataXferMech(self.taskHandle, "", DAQmx_Val_DMA), "DAQmxSetAODataXferMech")
                             
            self.errorCheck (self.nidaq.DAQmxCfgOutputBuffer (self.taskHandle, 2*self.numSampsPerChannel), 'DAQmxCfgOutputBuffer')
                                                 
            self.write_updated_buffer()
        
        #if self.dataBufferingEnabled is True write buffer a second time
        #if not enabled it is wriiten only once
        print('writing data buffer')
        self.write_updated_buffer()
                
        #self.errorCheck (self.nidaq.DAQmxStartTask(self.taskHandle), 'DAQmxStartTask')
        
        if not self.task_running:
            self.errorCheck (self.nidaq.DAQmxStartTask(self.taskHandle), 'DAQmxStartTask')
        
        self.task_running = True
        
        print('self.task_running>', self.task_running)
        '''
        print('end configure task >>>')        

    #def DAQ_configure_timing(self):
    #    #configure timing for parameters for the task
    #    self.errorCheck(self.nidaq.DAQmxCfgSampClkTiming(self.taskHandle, "",self.desired_freq, DAQmx_Val_Rising, DAQmx_Val_ContSamps, self.numSampsPerChannel), 'DAQmxCfgSampClkTiming')#1650
        
    
    def write_updated_buffer(self):
        print('\n<<< write_updated_buffer: self.numSampsPerChannel', self.numSampsPerChannel)
        #print 'printing self.data', self.data
        #print 'number of channels:', self.nChannels
        
        sampsPerChanWritten = int32()
                
        self.errorCheck (self.nidaq.DAQmxWriteAnalogF64(self.taskHandle, self.numSampsPerChannel,False, 10.0, DAQmx_Val_GroupByChannel, self.data, 
                                    byref (sampsPerChanWritten), None), 'DAQmxWriteAnalogF64')
        
        #if not self.task_running:
        #    self.errorCheck (self.nidaq.DAQmxStartTask(self.taskHandle), 'DAQmxStartTask')
            
        print('writing DAQ buffer sampsPerChanWritten:', sampsPerChanWritten.value)
                
    def stop_daq(self):
        
        print('\n<<< in stop_daq >>>')
        #clear DAQmx task and clear task if it running

        #self.nidaq.DAQmxStopTask(self.taskHandle)
        print ('<< DAQmxStopTask >>', self.nidaq.DAQmxStopTask(self.taskHandle))
        '''
        try:
            #self.analog_output.ClearTask()
            self.errorCheck (self.nidaq.DAQmxStopTask(self.taskHandle), 'DAQmxStopTask')
        except AttributeError:
            print('\n<<< DAQC...stop_daq No task running')
        else:
            self.errorCheck (self.nidaq.DAQmxClearTask(self.taskHandle), 'DAQmxClearTask')
            self.taskHandle = 0
            
            self.task_running = False
            print('\n<<< DAQC stop_daq stopping DAQ')
            print('self.task_running>', self.task_running)
        '''
        print('\n<<< stop_daq finished >>>')
    def reset_daq(self, module_name):
        '''
        Reset DAQ module specified in module_name
        '''
              
        print('*** DAQC reset_daq ***')
        print ('self.NI_devices\n', self.NI_devices )
                
        for j in self.NI_devices:
            temp_device, device_type = j 
            device = ctypes.create_string_buffer(32)
            device.value = temp_device.encode()
                       
            if module_name in temp_device:          #if device has 'Mod' in the name it passes if statement i.e cDAQ2Mod
                
                result = self.errorCheck(self.nidaq.DAQmxResetDevice(device), 'DAQmxResetDevice')
                 
                if result == 0:
                    print('*** <%s (%s)> DAQ has been reset ***' %(temp_device, device_type))
                else:
                    print('<%s> not reset, DAQ result code:%d' %(temp_device, result))
         
        if self.task_running:
            self.task_running = False
            print('self.task_running>', self.task_running) 
        
        print('*** End DAQC reset_daq ***')  
                      
    def zero_daq(self):
        
        print('*** zero_daq ***')
        
        for i in range (self.nChannels * self.numSampsPerChannel):
            self.data[i] = 0         

        if self.task_running:   #stop if task is running
            self.write_updated_buffer()
        else:
            self.configure()                                
            
        #writeFile(self.data)
        #self.configure()
        sleep(1)
        self.stop_daq()        
        
        print('*** DAQ zero complete ***') 
        
    def update_daq(self, volts, phaseOffsets, nthHarmonics, nthHarmonicsAmp, is_IR_Chassis, sys_frequencyX = 60.0 , sys_frequencyY = 60.0, ):
        # arguments are passed as a list i.e. [1.9,1.9,0.2,1.9,1.9,0.2,1.9,1.9,0.2]
        #      
        print('\n<<< in DAQC module update_daq X>>>')
        
        self.nthHarmonics = (ctypes.c_double * len (nthHarmonics))()
        self.nthHarmonicsAmp =  (ctypes.c_double * len(nthHarmonicsAmp))()
        
        sys_frequencyX = ctypes.c_double (sys_frequencyX)
        sys_frequencyY =  ctypes.c_double (sys_frequencyY)
        
        #print 'sys_frequencyX ', sys_frequencyX, type (sys_frequencyX)
        #print 'sys_frequencyY', sys_frequencyY, type (sys_frequencyY)
        #print 'len(volts)', len(volts)
        print('number of channel', self.nChannels)
        
        for index in range(len(volts)):
            self.amplitudes [index] = volts[index]
        
        #print 'len(phaseOffsets)', len(phaseOffsets)
        for index in range(len(phaseOffsets)):
            self.phaseOffsets [index]= phaseOffsets[index]
            
        #print 'len(nthHarmonics)', len(nthHarmonics)
        for index in range (len(nthHarmonics)):
            self.nthHarmonics[index] = nthHarmonics[index]
            
        #print 'len(nthHarmonicsAmp)', len(nthHarmonicsAmp)
        for index in range (len(nthHarmonicsAmp)):
            self.nthHarmonicsAmp [index] = nthHarmonicsAmp[index]                                   
              
        self.generateSineWave(sys_frequencyX, sys_frequencyY, is_IR_Chassis)
        sleep(1)
        
        if self.task_running:
            print('task is already running...writing new analog values')            
            #self.DAQ_configure_timing()      #added 11/21/15
            #if dataBufferingEnabled, stop task and start a new one
            #else just write new data
            if  self.dataBufferingEnabled:
                self.stop_daq()          
                self.configure()
            else:
                self.write_updated_buffer()
                    
        else:
            print('task isn not running...creating task')
            self.configure()
        
        print('\n<<< end DAQC module update_daq X>>>')
    

    def update_freq(self,  sys_frequencyX = 60.0 , sys_frequencyY = 60.0, is_IR_Chassis = True ):

        #print 'update_freq method'
        #print 'is_IR_Chassis', is_IR_Chassis

        sys_frequencyX = ctypes.c_double(sys_frequencyX)
        sys_frequencyY = ctypes.c_double(sys_frequencyY)

        self.generateSineWave(sys_frequencyX, sys_frequencyY, is_IR_Chassis)
        sleep(1)

        if self.task_running:
            print('task is already running...writing new analog values')
            # self.DAQ_configure_timing()      #added 11/21/15
            # if dataBufferingEnabled, stop task and start a new one
            # else just write new data
            if self.dataBufferingEnabled:
                self.stop_daq()
                self.configure()
            else:
                self.write_updated_buffer()

        else:
            print('task isn not running...creating task')
            self.configure()

    def errorCheck(self, error_code, func):
        print('\nin errorCheck method, error code %d <<%s>>' %(error_code, func))
        errBuff = ctypes.create_string_buffer(2048)
        
        if error_code < 0:
            self.nidaq.DAQmxGetExtendedErrorInfo(errBuff,2048)            
        elif error_code > 0:
            self.nidaq.DAQmxGetErrorString(error_code, errBuff, 2048)
        
        print(errBuff.value.decode("utf-8"))
        return error_code

    def _wait_for_device_ready(self, chassis_name, timeout=10.0, poll_interval=0.5):
        """Poll DAQmxGetDevProductType until the device responds after reset, or timeout expires."""
        device = ctypes.c_char_p(chassis_name.encode())
        buff = ctypes.create_string_buffer(256)
        elapsed = 0.0
        while elapsed < timeout:
            result = self.nidaq.DAQmxGetDevProductType(device, ctypes.byref(buff), 256)
            if result == 0:
                print(f"Device '{chassis_name}' ready after {elapsed:.1f}s: {buff.value.decode()}")
                return True
            print(f"Waiting for '{chassis_name}' to reboot... elapsed={elapsed:.1f}s (result={result})")
            sleep(poll_interval)
            elapsed += poll_interval
        print(f"Timeout: '{chassis_name}' did not respond within {timeout}s")
        return False

    def setup_daq_parameters(
                             harmonicAmplitudes, harmonicComponents, system_freq, dataBufferingEnabled = False):
        
        print('\n<<< in DAQC setup_daq_parameters >>>\n')
        self.dataBufferingEnabled = dataBufferingEnabled
                
        #sampleRate = 1800
        #sampleRate = rate 
                
        
        self.numSampsPerChannel = numSampsPerChannel #ifrom dnp_test2 module
        print('self.numSampsPerChannel type (self.numSampsPerChannel) >>', type (self.numSampsPerChannel))

        self.sampleRate = ctypes.c_double(sampleRate) #c_double(rate)
        self.nChannels = nchannels #c_double (nchannels)

        print('self.nChannels, type self.nChannels >>>', self.nChannels, type (self.nChannels))
        print('sampleRate', sampleRate, type (sampleRate))
        print('self.numSampsPerChannel', self.numSampsPerChannel, type (self.numSampsPerChannel))
        print('numSampsPerChannel', numSampsPerChannel, type (numSampsPerChannel))
        print ('physChan -> ', physChan)

        print('physChan -> ', physChan.encode())
                               
        self.physChan = ctypes.c_char_p(physChan.encode())
       
        #self.data = (c_double * (self.nChannels * self.numSampsPerChannel.value))()
        self.data = (ctypes.c_double * (self.nChannels * self.numSampsPerChannel))()
        #self.datanp= np.array(self.nChannels * self.numSampsPerChannel, dtype = np.double)
        self.amplitudes = (ctypes.c_double * self.nChannels)()
        self.phaseOffsets = (ctypes.c_double * self.nChannels)()
        self.dcOffsets = (ctypes.c_double * self.nChannels)
        self.harmonicsAmplitudes = (ctypes.c_double * 32)()
        self.harmonicComponents =  (ctypes.c_double * 32)()
        
        print('self.data', self.data)
        #print ('self.datanp', self.datanp)
               
        #initialize arrays
        self.amplitudes = [j for j in amplitudes]
        print('self.amplitudes', self.amplitudes, type (self.amplitudes), type (amplitudes[0]), self.amplitudes[0])
        self.phaseOffsets = [j for j in phaseOffsets]
        print('self.phaseOffsets', self.phaseOffsets)
        self.dcOffsets = [j for j in dcOffsets ]
        print('self.dcOffsets', self.dcOffsets)
        self.harmonicsAmplitudes = [j for j in harmonicAmplitudes]
        print('self.harmonicsAmplitudes', self.harmonicsAmplitudes)
        self.harmonicComponents = [j for j in harmonicComponents]
        print('self.harmonicComponents', self.harmonicComponents)
        
        #self.calculate_desired_frequency(system_freq)       #initialize self.desired_freq
        print ('\n<<< end DAQC setup_daq_parameters >>>\n')

                      
    '''
    def calculate_desired_frequency(self, system_freq):
        #adjust self.rate_hz when desired system frequency is less than 60        
        print 'calculating new self.desired_freq'
        #self.desired_freq = self.rate_hz*(system_freq/60.0)
        self.desired_freq = system_freq
        print 'done calculationg new self.desired_freq'
    '''
                
    def test(self):
                  
        #physChan = 'cDAQ4mod1/ao0:2,cDAQ4mod2/ao0:2,cDAQ4mod3/ao0:5'
        physChan = 'cDAQ5Mod1/ao0:2,cDAQ5Mod2/ao0:2,cDAQ5Mod4/ao0:5'
        nchannels = 12
        rate = 64800.0
        numSampsPerChannel = 1080
        sys_frequency = 60
        amplitudes = [7.2, 7.2, 7.2, 7.2, 7.2, 7.2, 3, 3, 3, 3, 3, 3]
        phaseOffsets = [0,-120,120,0,-120,120,-5.5,-125.5,114.5,-5.5,-125.2,114.5]
        dcOffsets = [0,0,0,0,0,0, 0,0,0,0,0,0]
        harmonicAmplitudes = [0,0,0,0,0,0, 0,0,0,0,0,0]
        harmonicComponents = [0,0,0,0,0,0, 0,0,0,0,0,0]
        
        self.setup_daq_parameters(physChan, nchannels, rate, numSampsPerChannel, amplitudes, phaseOffsets, dcOffsets, 
                                  harmonicAmplitudes, harmonicComponents, sys_frequency)
        
        self.generateSineWave(sys_frequency, 60,60)
        #execute d.getPhysChans() to get list of available channels
        #execute d.setPhysChanName(physical_channel) physical channel is one of the channels listed in d.getPhysChan
        self.configure()
        #d.reset_daq(physical_channel)
        #self.update_daq_settings(64800,12,1080)
                     
def main():
    global d
    #6800
    #physChan = 'cDAQ5Mod1/ao0:2,cDAQ5Mod2/ao0:2,cDAQ5Mod4/ao0:5'
    #physChan = 'cDAQ9184-1B3C9BEMod4/ao0:2, cDAQ9184-1B3C9BEMod4/ao3:5, cDAQ9184-1B3C9BEMod4/ao6:11'
    #nchannels = 12
    #rate = 64800.0
    #numSampsPerChannel = 1080
    #sys_frequency = 60
    #amplitudes = [7.2, 7.2, 7.2, 7.2, 7.2, 7.2, 3, 3, 3, 3, 3, 3]
    #phaseOffsets = [0,-120,120,0,-120,120,-5.5,-125.5,114.5,-5.5,-125.2,114.5]
    #dcOffsets = [0,0,0,0,0,0, 0,0,0,0,0,0]
    #harmonicAmplitudes = [0,0,0,0,0,0, 0,0,0,0,0,0]
    #harmonicComponents = [0,0,0,0,0,0, 0,0,0,0,0,0]

    #IntelliRupter
    #physChan = 'cDAQ1Mod1/ao0:2,cDAQ1Mod2/ao0:2, cDAQ1Mod3/ao0:2'
    #nchannels = 9

    #for IR collect one second worth of data
    #numSamples = SampleRate (samples/Sec) * interval
    #for interval of 1 second, numSamples = SampleRate
    #value of 99000 works good for IR with a few seconds lag in updating DAQ data
    #rate =  64800   # 99000
    #numSampsPerChannel = 64800 #99000

    #amplitudes = [1.9,1.9,0.1,1.9,1.9,0.1,1.9,1.9,0.1]
    #phaseOffsets = [0, 0, 90, 120.0, 120.0, 210.0, -120.0,-120.0, -30.0]
    #dcOffsets = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    #harmonicAmplitudes = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    #harmonicComponents = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    #nthHarmonicsAmp = [0.1, 0.1, 0.02, 0.1, 0.1, 0.02, 0.1, 0.1, 0.02]
    #nthHarmonics = [3.0,5.0,7.0,9.0]

    #sys_frequencyX = 60
    #sys_frequencyY = 60

    Sw6800_injection()
    #Sw6801M_injection()
    #IR_injection()

    #d = DAQmx ()
    #sleep(5)
    #d.listNI_DAQ_devices()
    #NI_module = get_NI_Module_name(physChan)
    #print 'NI_module', NI_module
    #d.reset_daq(NI_module)
    #d.reset_daq(physChan)
            
    #d.setup_daq_parameters(physChan, nchannels, rate, numSampsPerChannel, amplitudes, phaseOffsets, dcOffsets,
    #                          harmonicAmplitudes, harmonicComponents, sys_frequencyX )
    
    #d.generateSineWave(sys_frequencyX, sys_frequencyY, True)
    #update_daq(self, volts, phaseOffsets, nthHarmonics, nthHarmonicsAmp, is_IR_Chassis, sys_frequencyX=60.0,
    #           sys_frequencyY=60.0, )
    #d.update_daq(amplitudes, phaseOffsets,  nthHarmonics, nthHarmonicsAmp, True, sys_frequencyX, sys_frequencyY )
    #sleep(5)
    #d.configure()

def get_NI_Module_name(module_name):
        '''
        Get NI module prefix from NI_devices drop down list
        '''
        
        NI_module_name = re.search('cDAQ[\d]+Mod', module_name) 
        
        if NI_module_name:
            print(NI_module_name.group(), type (NI_module_name.group()))
        
        return NI_module_name.group()

def Q ():
    rate = 99000
    numSampsPerChannel = 99000

    amplitudes = [0, 1.9, 0.1, 0, 1.9, 0.1, 0, 1.9, 0.1]
    phaseOffsets = [0, 0, 90, 120.0, 120.0, 210.0, -120.0, -120.0, -30.0]
    dcOffsets = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    harmonicAmplitudes = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    harmonicComponents = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    nthHarmonicsAmp = [0.1, 0.1, 0.02, 0.1, 0.1, 0.02, 0.1, 0.1, 0.02]
    nthHarmonics = [3.0, 5.0, 7.0, 9.0]

    sys_frequencyX = 60
    sys_frequencyY = 59

    d.update_daq(amplitudes, phaseOffsets, nthHarmonics, nthHarmonicsAmp, True, sys_frequencyX, sys_frequencyY)

def Sw6800_injection():
    global d
    #6800
    physChan = 'cDAQ5Mod1/ao0:2,cDAQ5Mod2/ao0:2,cDAQ5Mod4/ao0:5'
    #physChan = 'cDAQ5Mod1/ao0:2'
    #physChan = 'cDAQ9184-1B3C9BEMod4/ao0:2, cDAQ9184-1B3C9BEMod4/ao3:5, cDAQ9184-1B3C9BEMod4/ao6:11'
    nchannels = 12
    rate = 64800 #64800
    numSampsPerChannel =  64800 #1080
    sys_frequency = 60
    amplitudes = [4.1,4.1, 4.1, 4.1, 4.1, 4.1, 3, 3, 3, 3, 3, 3]
    #phaseOffsets = [0, -120, 120, 0, -120, 120, -22.5, -141.5, 130.5, -5.5, -125.5, 114.5]
    phaseOffsets = [0,-120,120,0,-120,120,-5.5,-125.5,114.5,-5.5,-125.5,114.5]
    phase_mask = [0,0,0,0,0,0,-15, -10, -10, 0,0,0]

    dcOffsets = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    harmonicAmplitudes = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    harmonicComponents = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    nthHarmonicsAmp = [0.1, 0.1, 0.02, 0.1, 0.1, 0.02, 0.1, 0.1, 0.02]
    nthHarmonics = [3.0, 5.0, 7.0, 9.0]
    harmonics_values = [(3,.25),(5,.25),(7,.25), (9,.25) ]

    phaseOffsets = np.sum([phaseOffsets, phase_mask], axis=0)


    sys_frequencyX = 60
    sys_frequencyY = 60
    channels_to_modify = [0, 1, 2, 6, 7, 8]
    #channels_to_modify = [0,1,6,7]
    d = DAQmx()
    # sleep(5)
    # d.listNI_DAQ_devices()
    # NI_module = get_NI_Module_name(physChan)
    # print 'NI_module', NI_module
    # d.reset_daq(NI_module)
    d.reset_daq(physChan)

    #d.setup_daq_parameters(physChan, nchannels, rate, numSampsPerChannel, amplitudes, phaseOffsets, dcOffsets,
    d.setup_daq_parameters(physChan, nchannels, rate, numSampsPerChannel, amplitudes, phaseOffsets, dcOffsets,
                               harmonicAmplitudes, harmonicComponents, sys_frequencyX)
    #generate sine waves
    #d.generateSineWave(sys_frequencyX, sys_frequencyY, False, include_noise = True,  include_harmonics = True, noise_std = 0.18 )
    d.generateSineWave(sys_frequencyX, sys_frequencyY, channels_to_modify, False, include_noise=True,
                       include_harmonics=True, noise_std=0.15,highest_harm=31, SNR_db=25)

    # update_daq(self, volts, phaseOffsets, nthHarmonics, nthHarmonicsAmp, is_IR_Chassis, sys_frequencyX=60.0,
    #           sys_frequencyY=60.0, )

    print ('\n++++ continue 6880 injection +++++')
    #d.update_daq(amplitudes, phaseOffsets, nthHarmonics, nthHarmonicsAmp, True, sys_frequencyX, sys_frequencyY)
    #start NI task

    #configure NI injection
    d.configure()
    #display harnonics content graph
    d.fast_fourier_transform()
    #display current and voltage injection graphs
    # first argument number of voltage channels, second arguement number of current channels
    #d.plot_graphs(0, 6)
    d.plot_graphs(6, 6, no_switches=2)

    message="\n***Menu*** Type\np = voltage and current graphs\nh = harmonic content FFT graph\n'stop' = stop injection\n>"

    #wait loop
    while True:
        user_input = input (message) #"\nType 'stop' to end injection, 'm' for menu...")
        if user_input == "stop":
            d.stop_daq()
            return False
        elif user_input == "h":
            #fft_ouput, frequencies = d.fast_fourier_transform(False)
            d.fast_fourier_transform()
        elif user_input == "p":
            d.plot_graphs(6, 6, no_switches=2)
        elif user_input == "m":
            print (message)

def Sw6801M_injection():
    global d
    #6800
    #physChan = 'cDAQ5Mod1/ao0:2,cDAQ5Mod2/ao0:2,cDAQ5Mod4/ao0:5'
    #physChan = 'cDAQ5Mod1/ao0:2'
    physChan = 'cDAQ9188-1C31932Mod6/ao0:2,cDAQ9188-1C31932Mod7/ao0:2,cDAQ9188-1C31932Mod8/ao0:2'
    #physChan = 'cDAQ9184-1B3C9BEMod4/ao0:2, cDAQ9184-1B3C9BEMod4/ao3:5, cDAQ9184-1B3C9BEMod4/ao6:11'
    nchannels = 9
    rate = 64800 #64800
    numSampsPerChannel =  64800 #1080
    sys_frequency = 60
    amplitudes = [6.2, 6.2, 6.2, 6.2, 6.2, 6.2, 3, 3, 3]
    phaseOffsets = [0, -120, 120, 0, -120, 120, -22.5, -141.5, 130.5]
    #phaseOffsets = [0,-120,120,0,-120,120,-5.5,-125.5,114.5,-5.5,-125.5,114.5]
    dcOffsets = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    harmonicAmplitudes = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    harmonicComponents = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    nthHarmonicsAmp = [0.1, 0.1, 0.02, 0.1, 0.1, 0.02, 0.1, 0.1, 0.02]
    nthHarmonics = [3.0, 5.0, 7.0, 9.0]

    sys_frequencyX = 60
    sys_frequencyY = 60
    #channels_to_modify = []
    channels_to_modify=[0,1,2,6,7,8]

    d = DAQmx()
    # sleep(5)
    # d.listNI_DAQ_devices()
    # NI_module = get_NI_Module_name(physChan)
    # print 'NI_module', NI_module
    # d.reset_daq(NI_module)
    d.reset_daq(physChan)

    #d.setup_daq_parameters(physChan, nchannels, rate, numSampsPerChannel, amplitudes, phaseOffsets, dcOffsets,
    d.setup_daq_parameters(physChan, nchannels, rate, numSampsPerChannel, amplitudes, phaseOffsets, dcOffsets,
                               harmonicAmplitudes, harmonicComponents, sys_frequencyX)
    #generate sine waves
    d.generateSineWave(sys_frequencyX, sys_frequencyY, channels_to_modify, False, include_noise = True, include_harmonics = falseTrue, noise_std = 0.25 )

    # update_daq(self, volts, phaseOffsets, nthHarmonics, nthHarmonicsAmp, is_IR_Chassis, sys_frequencyX=60.0,
    #           sys_frequencyY=60.0, )

    print ('\n++++ continue 6880 injection +++++')
    #d.update_daq(amplitudes, phaseOffsets, nthHarmonics, nthHarmonicsAmp, True, sys_frequencyX, sys_frequencyY)
    #start NI task

    #configure NI injection
    d.configure()
    #display harnonics content graph
    d.fast_fourier_transform()
    #display current and voltage injection graphs
    d.plot_graphs(6, 3, no_switches =2)

    message="\n***Menu*** Type\np = voltage and current graphs\nh = harmonic content FFT graph\n'stop' = stop injection\n>"

    #wait loop
    while True:
        user_input = input (message) #"\nType 'stop' to end injection, 'm' for menu...")
        if user_input == "stop":
            d.stop_daq()
            return False
        elif user_input == "h":
            #fft_ouput, frequencies = d.fast_fourier_transform(False)
            d.fast_fourier_transform()
        elif user_input == "p":
            d.plot_graphs(0, 6)
        elif user_input == "m":
            print (message)




def IR_injection():

    # for IR collect one second worth of data
    # numSamples = SampleRate (samples/Sec) * interval
    # for interval of 1 second, numSamples = SampleRate
    # value of 99000 works good for IR with a few seconds lag in updating DAQ data
    # rate =  64800   # 99000
    # numSampsPerChannel = 64800 #99000

    # amplitudes = [1.9,1.9,0.1,1.9,1.9,0.1,1.9,1.9,0.1]
    # phaseOffsets = [0, 0, 90, 120.0, 120.0, 210.0, -120.0,-120.0, -30.0]
    # dcOffsets = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    # harmonicAmplitudes = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    # harmonicComponents = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    nthHarmonicsAmp = [0.1, 0.1, 0.02, 0.1, 0.1, 0.02, 0.1, 0.1, 0.02]
    nthHarmonics = [3.0, 5.0, 7.0, 9.0]

    sys_frequencyX = 60
    sys_frequencyY = 60

    physChan = 'cDAQ9184-1B3C9BEMod4/ao0:2, cDAQ9184-1B3C9BEMod4/ao3:5, cDAQ9184-1B3C9BEMod4/ao6:11'

    d = DAQmx()
    # sleep(5)
    # d.listNI_DAQ_devices()
    # NI_module = get_NI_Module_name(physChan)
    # print 'NI_module', NI_module
    # d.reset_daq(NI_module)
    d.reset_daq(physChan)

    d.setup_daq_parameters(physChan, nchannels, rate, numSampsPerChannel, amplitudes, phaseOffsets, dcOffsets,
                           harmonicAmplitudes, harmonicComponents, sys_frequencyX)

    # d.generateSineWave(sys_frequencyX, sys_frequencyY, True)
    # update_daq(self, volts, phaseOffsets, nthHarmonics, nthHarmonicsAmp, is_IR_Chassis, sys_frequencyX=60.0,
    #           sys_frequencyY=60.0, )
    d.update_daq(amplitudes, phaseOffsets, nthHarmonics, nthHarmonicsAmp, True, sys_frequencyX, sys_frequencyY)
    # sleep(5)
    # d.configure()


def split_list(lst, n):
    return [lst[i:i + n] for i in range(0, len(lst), n)]

def start_daq():
    
    d.generateSineWave()
    d.configure()
    
def stop_daq():
    #d.zero_daq()
    d.stop_daq()

def update_freq(freq_x,freq_y):
    d.update_freq(freq_x, freq_y, True)
       
def writeFile(data, func_name):
    print('in writeFile function')
    d = DAQmx ('cDAQ1mod1/ao0:2,cDAQ1mod2/ao0:2,cDAQ1mod3/ao0:2')
    handle = open(r'c:\logfiles\dataArray.txt', 'a') 
    
    for index in range (len (data)):
        text = "%i, %f\n" %(index, data[index])
        handle.write(text)
    
    text = '*** End ****' + func_name
    handle.write(text+ '\n')
        
    handle.close()
        
if __name__ == '__main__':
    main()
