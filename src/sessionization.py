import sys, argparse
from datetime import datetime, timedelta
import warnings
from itertools import islice

class SessionParser(object):

    def __init__(self,output_path,inactivity_period=2,fields=None):

        try:
            self.period = int(inactivity_period)
        except:
            raise ValueError('inactivity_period must be an integer number of seconds.')

        self.activeUsers = {}

        self.currentTime = None

        self.output = output_path

        # Default fields (in case log format has changed)
        self.fields = {
            'ip':0,
            'date':1,
            'time':2
        }
            #'zone':3,
            #'cik':4,
            #'accession':5,
            #'extention':6,
            #'code':7,
            #'size':8,
            #'idx':9,
            #'norefer':10,
            #'noagent':11,
            #'find':12,
            #'crawler':13,
            #'browser':14

        # give each parsed line a unique ID to avoid any order output ambiguity.
        self.lineID = 0

    def parseRequests(self,requests):


                for line in requests:

                    # increment unique line id
                    self.lineID += 1

                    # split the line into arguments
                    args = line.split(',')
                    #print args

                    # pick out the arguments that are needed
                    uip = args[ self.fields['ip'] ]
                    date = args[ self.fields['date'] ]
                    time = args[ self.fields['time'] ]

                    dtime = datetime.strptime(date + ' ' + time,
                                              '%Y-%m-%d %H:%M:%S')

                    # Check and store time
                    if self.currentTime is None:
                        self.currentTime = dtime
                        delta = timedelta(seconds=0)
                    else:
                        delta = dtime - self.currentTime
                        self.currentTime = dtime

                    #print uip, self.currentTime, delta.seconds

                    # if the time has changed check for terminated sessions
                    if delta.seconds > 0:
                        print self.currentTime
                        print self.activeUsers.keys()
                        self.detectTerminatedSessions()

                    # Check if user is active, and store or update as necessary
                    if uip in self.activeUsers.keys():
                        u = self.activeUsers[uip]
                        u.update(self.currentTime)
                    else:
                        u = User(self.lineID,uip,self.currentTime)
                        self.activeUsers.update({uip:u})

    def detectTerminatedSessions(self):

        terminatedSessions = []

        # iterate through active users
        for uip in self.activeUsers.keys():

            user = self.activeUsers[uip]

            # Check if user's session has expired
            if (self.currentTime - user.latest_time).seconds > self.period:

                terminatedSessions.append(user)

                # remove user from active users
                self.activeUsers.pop(uip)


        # sort so that sessions print in the correct order
        terminatedSessions.sort(key=lambda x: (x.start_time,x.lid))

        # write to output file
        #with self.output as f:
        for user in terminatedSessions:
            print user.printString()
            self.output.write( user.printString())

    def terminateRemaining(self):

        terminatedSessions = [ self.activeUsers[ip] for ip in self.activeUsers.keys()]

        # reset active users
        self.activeUsers = {}

        # sort so that sessions print in the correct order
        terminatedSessions.sort(key=lambda x: (x.start_time,x.lid) )

        # write to output file
        #with self.output as f:
        for user in terminatedSessions:
            print user.printString()
            self.output.write( user.printString())

class User(object):

    def __init__(self,lid,ip,start_time):

        # identifying information
        self.lid = lid
        self.ip = ip

        # times
        self.start_time = start_time
        self.latest_time = start_time

        self.num_docs = 1

        # check for valid ip
        # check for valid start time

    def update(self,time):

        # store the most recent time
        self.latest_time = time

        # increment the number of documents
        self.num_docs += 1

    def sessionLength(self):

        return 1 + (self.latest_time - self.start_time).seconds

    def printString(self):

        return self.ip + ',' + str(self.start_time) + ',' + str(self.latest_time) + \
                ',' + str(self.sessionLength()) + ',' + str(self.num_docs) + '\n'




if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(description=
                                     'Parse SEC EDGAR log into Sessions.')

    parser.add_argument('log_file', metavar='log*.csv',
                        type=argparse.FileType('r'),
                        help='EDGAR weblog data file (csv)')
    parser.add_argument('inactivity_period', metavar='inactivity_period',
                        type=argparse.FileType('r'),
                        help='text file storing integer inactivity period')
    parser.add_argument('output_file', metavar='output',
                        type=argparse.FileType('a'),
                        help='output text file with session information',
                        default=sys.stdout)

    args = parser.parse_args()


    # Store inactivity period
    with args.inactivity_period as f:

       inactivity_content = [x.rstrip() for x in f.readlines()]

       try:
           inactivity_period = int(inactivity_content[0])
       except:
            raise ValueError('inactivity_period must be an integer number of seconds.')

       if len(inactivity_content) > 1:
           warnings.warn("Only the the first line of file considered for inactivity period.",
                         SyntaxWarning)
       print 'Inactivity period:', inactivity_period, 'seconds'

    sp = SessionParser(args.output_file,inactivity_period=inactivity_period)

    line_buffer = 100
    with args.log_file as f:

        # skip initial line (could use this to make sure the correct column is
        # used)
        line = f.readline()
        print line

        while True:
            line_gen = list(islice(f, line_buffer))
            if not line_gen:
                break
            sp.parseRequests(line_gen)

        # clean up at end of file
        sp.terminateRemaining()


