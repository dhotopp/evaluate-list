#!/usr/bin/env python3
#
# This program focuses on methods to run processes; specifically with and w/o multithreading and multiprocessing.  
# I may add some more error checking eventually and test on a Linux box.
#
# Copyright 2019: Dan Hotopp <d.hotopp@gmail.com> | <dhotopp@nyx.net>
# License: https://opensource.org/licenses/MIT
# Github link: https://github.com/dhotopp/evaluate-list
#
# Revision History:	20190506 - Initial release
#					20190512 - Added psutil functions to properly kill processes (parent and children) if timed-out
#							   Added -i --interval option for process (not pool) status updates 
#					20190616 - Added support to read list of urls from cli or file
#
# Known issues:
#	- KeyboardInterrupts don't always exit cleanly
#
# Example: evallist.py -d -mThreadProcess -p20  -c".\showargs-random.bat -max 60" -t15 -i5
#
# Excellent reference URLs: 
#	http://sebastianraschka.com/Articles/2014_multiprocessing.html#
#	https://chriskiehl.com/article/parallelism-in-one-line
#	https://pymotw.com/2/multiprocessing/basics.html
#
# Import various functions using differnt options
# Nice reference: https://docs.python-guide.org/writing/structure/#modules
import sys, os, argparse, datetime, time, subprocess, psutil, glob, re
from collections import ChainMap
from pathlib import Path
import multiprocessing as mp
import multiprocessing.dummy as mpthread
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
#from urllib.request import urlopen

# Set initial values
Start=time.time()
defaults = {'debug':False, 'timeout':100, 'method':'ThreadPool_async', 
	'processors':'4','cmd':'showargs-random.bat','interval':10, 'list':'urllist.txt'} 

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--cmd', help='Default: ' +defaults['cmd'])
parser.add_argument('-d', '--debug', action='store_true', help='Show debug info')
parser.add_argument('-i', '--interval', help='Default process status interval: ' +str(defaults['interval']) +'(secs)' )
#parser.add_argument('-l', '--list', help='Default list(s) to evaluate: ' +str(defaults['list']), action='append')
parser.add_argument('-l', '--list', help='Default list file(s) to evaluate: ' +str(defaults['list']))
parser.add_argument('-m', '--method',  choices=['Process','ThreadProcess','Pool','ThreadPool', 'Pool_async', 
	'ThreadPool_async', 'NoPool'], help='Default: ' +defaults['method'])
parser.add_argument('-p', '--processors', help='Default: ' +defaults['processors'])
parser.add_argument('-t', '--timeout', help='Default: ' +str(defaults['timeout']) +'(secs)')
args = parser.parse_args()

cli_args = {k:v for k, v in vars(args).items() if v}
#d = ChainMap(cli_args, os.environ, defaults)
opts = ChainMap(cli_args, defaults)

# Set variables 
Cmd = opts['cmd']
Debug = opts['debug']
Interval = int(opts['interval'])
Method = opts['method']
Processors = int(opts['processors'])
Timeout = int(opts['timeout'])

urlalias={}

# Get the number of processors available (not supported with multiprocessing.dummy)
#num_processes = mp.cpu_count()
num_processes = Processors

# One method to show time
def now ():
	now = datetime.datetime.now()
	return (now)
#	return now.strftime("%Y-%m-%d %H:%M:%S")

# Another way to to show time - compatible with SQL
def gettime():
	ts = time.time()
	timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
	return (timestamp)

# Referenced for possible future use.
# Method to fetch URL pages or headers.
#html = urlopen('http://www.google.com/').info()
#print(html.info())
#print(html.read())
#print (html)

#def getinfo(x):
#	info = urlopen(x).info()
#	print ("Info for %s:\n%s" % (x,info))
#	return (info)

def dowork(this):
	#if Debug: print ("\nDo work for ",this,now(),"\n")
	subproc=work(this, None)
	return (subproc)

def work(item, workoptions):
	allargs = cmdopts = ''
	NewCmd = Cmd
	if Debug:
		print ('Processing work for ',item,now())
		if workoptions: print ('WorkOpions: %s for %s'% (workoptions,item))
		print ('Parent Process ID: %s for %s' % (os.getppid(),item))
		print ('Process ID: %s for %s'	% (os.getpid(),item))
	if len(Cmd.split()) > 1:
		if Debug: print ("Splitting Cmd: ",Cmd)
		items = Cmd.split()
		NewCmd = items[0]
		cmdopts = items[1:len(items)]
		
	#if Debug: print ("***urlalias: ", dict(urlalias))
	
	allargs = str(item)
	allargs = "--ppid ".join([allargs,str(os.getppid())])
	allargs = "--pid ".join([allargs,str(os.getpid())])
	if Debug: print ('Subprocess Cmd: ',NewCmd,*cmdopts,allargs)
	if not cmdopts: subp = subprocess.Popen([NewCmd,allargs])
	if cmdopts: subp = subprocess.Popen([NewCmd,*cmdopts,allargs])
	subp_pid = psutil.Process(subp.pid)
	if Debug: print ("Subprocess PID: ", subp_pid)
	
	try:
		subp_pid.wait(timeout=Timeout)
	except psutil.TimeoutExpired as e:
		for subp_child in subp_pid.children(recursive=True):  # or subp_pid.children() for recursive=False
			print ("Child killed: ",subp_child,allargs)
			try:
				subp_child.kill()
			except psutil.NoSuchProcess:
				pass
		print ("Parent killed: ", subp.pid, item)
		try:
			subp_pid.kill()
		except psutil.NoSuchProcess:
			pass
		print (e)

	return(str(subp_pid) + " for " + item)
# End of work
	
def main():
	urls = []
	i = 0
	if Debug: 
		for k, v in sorted(opts.items()):
			print (k, '-->', v)

	# Start timing this sucker
	print ("Start time: ", now())
	start_time = now() #Used for timing
	Start = time.time()	 #Used for periodic checks
	
	# Get list of URLs.  
	if glob.glob(opts['list']):  # check to see if they are files
		for list_entry in glob.glob(opts['list']):
			if Debug: print ("list_entry: ",list_entry)
		
			# Check to see if it's a cmds file.  If it is, parse it and run commands.
			listfile = Path(list_entry)
			if listfile.is_file(): 
				if Debug: print ("Using file:", listfile)
				listlines =[]
				with open(listfile) as lfile:
					#listlines = lfile.readlines()
					for line in lfile:
						if re.search(r"^\s*[#!]+.*$", line): continue
						l=re.findall(r"^\s*(.*)$", line) 
						#l=re.findall(r"^\s*([a-zA-Z0-9-:/. ]+)#*.*$", line) # Ingore past # char
						if l: 
							if Debug: print ("Adding entry:", l[0])
							listlines.append(l[0])
				# Remove whitespace characters like `\n` at the end of each line1
				listlines = [x.strip() for x in listlines] 
				if Debug: print ("URLs:  ", listlines)
				urls = urls + listlines
			# End of using file entries
	else:
		if Debug: print ("Not a file, so using -l | --list values")
		urls = re.compile('[ ,]').split(opts['list']) #split -l argument on spaces or commas
		
	print ("All URLs: ", urls)
	
	for u in urls:
		#if Debug: print (u)
		#urlalias[u]="Alias-"+u
		#if Debug: print ("Entries added:\n",u,urlalias[u])
		#print ("re: ",u.r"^\w*")

		u = u + " --alias " + u.replace(":", "-").replace("/", "_")
		if Debug: print ("Entry updated:\n", u)

	#if Debug: print ("urlalias keys: ", list(urlalias.keys()))
	#if Debug: print ("urlaliases: ", dict(urlalias))
	
	exit()		
#---			

	# Evaluate urls with multi-processor.Process or Pool method
	if Method == 'Process' or Method == 'ThreadProcess':
		EvalList_Process(urls)
	else:
		EvalList_Pool(urls)
	
	end_time = now()
	if Debug: print ("All evals completed... ",gettime())
	print("\nTotal time: {}".format(end_time - start_time))
	return (0)
# End of main

def EvalList_Process(mylist):
	# Use multiprocessing.Process method. Allows simple entry additions to process list
	i=0
	values = {}
	elements = ['index','url','time']
	for el in elements:
		values[el]=None
	entries = {}
	if Debug: print ("EvalList_Process: ", (list(mylist)))
	# Multi-element dictionary used as an example
	for entry in mylist:
		i += 1
		for el in elements:
			if el=='index':	values[el]=i
			if el=='url':	values[el]=entry
			if el=='time':	values[el]=gettime()
		entries[i]=values.copy()
	if Debug: print ("Entries updated:\n",dict(entries),"\n")

	#Method to loop through key value pairs 
	if Debug: 
		for k,v in sorted(entries.items()):
			print (k, '-->', v)
		
	#Other method to loop though key value pairs 
	#for indx in (entries):
	#	print ("indx: ", indx)
	#	for el in elements:
	#		print ("indx,el: ",indx,el,entries[indx][el])
			
	len_procs = len(entries.items())
	if Debug: print ("+++ Number of processors available: %s" % (len_procs))
	threads = []
	threadentries = {}
	while entries or threads:
		# if we aren't using all the processes AND there is still data entries to
		# evaulate, then spawn another thread
		try:
			curr_ent=next(iter(entries),None)
			#if Debug and curr_ent: print ("Current entries: ",dict(entries))
		except StopIteration:
			if Debug: print ("Done with iterations")
			raise
		if (len(threads) < num_processes) and curr_ent:
			currententry=entries[curr_ent]['url']
			if Debug: print ("Current entry: ",currententry)
			entries.pop(curr_ent)
			if Method == 'Process':
				p = mp.Process(target=dowork,args=[currententry])
			else:
				p = mpthread.Process(target=dowork,args=[currententry])
			p.start()
			if Debug: print ("Appending ",p)
			threads.append(p)
			threadentries[p]=currententry
		else:
			for thread in threads:
				if not thread.is_alive():
					if Debug: print ("Removing thread:",thread,now())
					threads.remove(thread)
			time.sleep(.2)
						
		elapsed_time =	int((time.time()-Start))		
		if elapsed_time and elapsed_time % Interval == 0 and Debug: 
			#if threads: print ("\nElapsed time for %s: %.2fs" % (threads,(time.time()-Start)))
			#for thread in threads:
			#print ("Current entries list as of %s:" % (now()))
			#for k, v in entries.items():
			#	print (k, '-->', v)
			#print ("Current thread list as of %s:" % (now()))
			#for t in threads:
			#	print (t)
			print ("\nThread entries list as of %s (%.2fs elapsed):" % (now(),(time.time()-Start)))
			for k, v in threadentries.items():
				if k.is_alive(): print (k, '-->', v)
			time.sleep(1)  # This allows for a very short sleep time above

	return (0)			
# End of EvalList_Process

def EvalList_Pool(mylist):
	# If mylist is less than num_processes, then reset num_processes
	use_num_processes = num_processes
	if len(mylist) < use_num_processes: 
		if Debug: print ("List entries (%s) < num_processes (%s) " % (len(mylist),use_num_processes))
		use_num_processes =	 len(mylist)
	# Make the Pool of workers
	if Method == 'Pool' or Method == 'Pool_async':
		pool = Pool(use_num_processes)
	elif Method == 'ThreadPool' or Method == 'ThreadPool_async':
		pool = ThreadPool(use_num_processes)

	# Evaulate list in their own threads and return the results
	if Method == 'Pool' or Method == 'ThreadPool':
		#if Debug: print ("dowork output: ",dowork)
		results = pool.map(dowork, mylist)
	elif Method == 'Pool_async' or Method == 'ThreadPool_async':
		results = pool.map_async(dowork, mylist)
	elif Method == 'NoPool':
		print ("method is ",Method)
		results = map(dowork, mylist)

	# Close the pool and wait for the work to finish
	try:
		if Method != 'NoPool' :
			pool.close()
			pool.join()
			if Debug: print ("Results for %s:" % (Method))
		if Method == 'Pool' or Method == 'ThreadPool' or  Method == 'NoPool':
			for r in results: 
				if Debug: print (r)
		elif (Method == 'Pool_async' or Method == 'ThreadPool_async'):
			async_results = results.get()
			for r in async_results: 
				if Debug: print (r)
	except (KeyboardInterrupt) as e:
		print ("Keyboard interrupt received while closing pool close and join.\n",e)
	return (0)					
# End of EvalList_Pool
	
if __name__ == '__main__':
	main()	
	
("""
	# Define test URLs 
	urls = [
	'http://www.startpage.com This has other arguments',
	'http://www.python.org',
	'http://www.python.org/about/',
	'http://www.onlamp.com/pub/a/python/2003/04/17/metaclasses.html',
	'http://www.python.org/doc/',
	'http://www.python.org/download/',
	'http://www.python.org/getit/',
	'http://www.python.org/community/',
	'https://wiki.python.org/moin/',
	'http://planet.python.org/',
	'https://wiki.python.org/moin/LocalUserGroups',
	'http://www.python.org/psf/',
	'http://docs.python.org/devguide/',
	'http://www.python.org/community/awards/'
	# etc..
	]
""")
