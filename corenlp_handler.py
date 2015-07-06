# with annotator:
# java -cp "/Users/tubi/Documents/courses/sensei/stanford-corenlp-full-2015-04-20/*" -Xmx2g -mx5g edu.stanford.nlp.sentiment.SentimentPipeline -file sampleDataOnForumS/81043636.ofs.in.xml

# with sentiment analysis only
# java -cp "/Users/tubi/Documents/courses/sensei/stanford-corenlp-full-2015-04-20/*" -mx2g edu.stanford.nlp.sentiment.SentimentPipeline -file sampleDataOnForumS/81043636.ofs.in.xml

# 
# running and output 
# python corenlp3.py -c "/Users/tubi/Documents/courses/sensei/stanford-corenlp-full-2015-04-20/*" -i en/362778020.ofs.in.xml -o en/362778020.ofs.t.csv


from optparse import OptionParser
from subprocess import Popen, PIPE
import pexpect
import re, os.path, os, subprocess, numpy as np, pandas as pd, time

CORENLP_CMD = """
java -cp '{classpath}' -mx{memory}g edu.stanford.nlp.sentiment.SentimentPipeline -stdin"""

PROCESS_INPUT_CMD = """
grep -E '<s id="s[0-9]*">.*</s>' {input} >> {temp_file}"""

TEMP_FILE = '.input.txt'

JAVA = "java"

def command(classpath=None, input=None, memory="4"):
    d = {'classpath': classpath, 'memory': memory}
    d.update(globals())
    return CORENLP_CMD.format(**d).replace("\n", " ")

def cleanup():
	if os.path.isfile(TEMP_FILE):
		os.remove(TEMP_FILE)
	if os.path.isfile(TEMP_FILE + ".xml"):
		os.remove(TEMP_FILE + ".xml")

def extract_comment(s):
	if s.find('[') == 0 and s.find(']') != -1:
		return s[s.find(']')+1:]
	return s


def main():                          
	start = time.time()
	

	usage = "usage: %prog [options]"

	parser = OptionParser(usage=usage)
	parser.add_option("-c", "--classpath",  action = "store", dest = "classpath",  help = "set location of CoreNLP")
	parser.add_option("-i", "--input",      action = "store", dest = "input",      help = "set input folder")
	parser.add_option("-m", "--memory",     action = "store", dest = "memory",     help = "set RAM memory (in GB), default: 4")
	parser.add_option("-o", "--output",     action = "store", dest = "output",     help = "[optional] set output folder, default: current folder")

	(options, args) = parser.parse_args()
	if (options.classpath is None) or (options.input is None):
		parser.error("incorrect number of arguments")

	### Argument checking
	inp = options.input
	if not os.path.exists(inp): 
		print 'Input file or folder does not exist'
		return 0

	#corenlp_cmd = command(classpath = options.classpath,  memory = options.memory)
	#print corenlp_cmd

	if os.path.isdir(inp):
		files = os.listdir(inp)
		for f in files:
			if '.xml' in f:
				process_file(f, inp, options.output, options.classpath, options.memory)

	else:
		print 'Input path is not a folder'
		return

	print '\n========= DONE ========='
	print "elapsed: {}s \n".format( int( round( time.time() - start )))


def process_file(input_file, input_dir, output_dir, classpath, memory = '4'):
	cleanup()

	process_input_cmd = PROCESS_INPUT_CMD.format(input = input_dir + '/' + input_file, temp_file = TEMP_FILE).replace("\n", " ")
	preprocess_output = subprocess.check_output(process_input_cmd, shell=True)
	print preprocess_output
	
	infile = pd.read_csv(TEMP_FILE, header=None, names=['sentence'], sep='<s id=>', engine='python')
	infile['id'] = infile.sentence.map(lambda s: re.match(r'(<s id=")(s[0-9]+)(">.*)(</s>)', s).group(2) )
	infile.sentence = infile.sentence.map(lambda s: re.match(r'(<s id="s[0-9]+">)(.*)(</s>)', s).group(2) )

	### match the comments
	# infile.sentence = infile.sentence.map(lambda s: re.match(r'^(\[.*\])*(.*)', s).group(2) )
	infile.sentence = infile.sentence.map(lambda s: extract_comment(s))

	# corenlp_cmd = 'java -cp "/Users/tubi/Documents/courses/sensei/stanford-corenlp-full-2015-04-20/*" -mx2g edu.stanford.nlp.sentiment.SentimentPipeline -stdin'
	corenlp_cmd = 'java -cp ' + '"' + classpath + '"' + ' -mx' + memory + 'g' + ' edu.stanford.nlp.sentiment.SentimentPipeline -stdin'
	print corenlp_cmd
	corenlp = pexpect.spawn(corenlp_cmd)
	corenlp.expect('Processing will end when EOF is reached.')
	print "### Processing file ", input_file
	print 

	infile['outcome'] = ''
	re_seq = re.compile(r'( +( Very negative| Negative| Neutral| Positive| Very positive)\r*\n*)+', re.MULTILINE)
	# re_seq = re.compile(r' +( Very negative| Negative| Neutral| Positive| Very positive)') - match only single line

	sentences_error = []

	for idx, s in enumerate(infile.sentence.values):
		print idx, s
		corenlp.sendline(s)
		try:
			corenlp.expect(re_seq, timeout=20)
		except pexpect.TIMEOUT:
			print 'timeout - restart the process'
			corenlp.kill(0)  # kills the subprocess and create a new one
			corenlp = pexpect.spawn(corenlp_cmd)
			corenlp.expect('Processing will end when EOF is reached.')
			corenlp.sendline(s)
			corenlp.expect(re_seq, timeout=120)
			print 'sentiment: ', ' '.join([s_.strip() for s_ in corenlp.after.split('\r\n')]) 
			continue

		out = corenlp.after
		sentiments = ' '.join([s_.strip() for s_ in out.split('\r\n')]) 
		print 'sentiment: ', sentiments
		infile.outcome.iloc[idx] = sentiments

	corenlp.close(force=True)
	
	infile = infile[['id', 'sentence', 'outcome']]
	if (output_dir == None) or (not os.path.exists(output_dir)):
		print 'output folder does not exist, results are produced in current folder'
		output_dir = '.' 

	infile.to_csv(output_dir + '/' + input_file + '.csv', index=False, header=False)	
	
	
	
if __name__ == "__main__":
    main()
	
# Multiple emotions: s68 s85 s95 - all single sentence
# s141



