import sys, argparse
import warnings
from datetime import datetime, timedelta
from itertools import islice

class SessionParser(object):
    """Parser for SEC EDGAR log data in csv format
    Usage::

        >>> from sessionization import SessionParser
        >>> input = open('log.csv','r')
        >>> ouput = open('output.txt','w')
        >>> sp = SessionParser(output)
        >>> sp.parse_requests(input)
        >>> sp.terminate_remaining_sessions()

    :param output: File object or generator with csv log data
    :param inactivity_period: Integer number of seconds beyond which a
                                a session is terminated (default = 2).
    :param fields: Dictionary with integer csv column number referenced by
                    field string. (default = {'ip':0, 'date':1, 'time':2}).
    """
    def __init__(self,output,inactivity_period=2,fields=None):

        # store active users in dictionary with ip address as the key
        self.active_users = {}

        # store the current time as a datetime object
        self.current_time = None

        # give each parsed line a unique ID to avoid any order output ambiguity.
        self.line_id = 0

        # file object to write output to
        self.output = output

        try:
            self.inactivity_period = int(inactivity_period)
        except:
            raise ValueError('`inactivity_period` must be an integer number of seconds.')

        # Default fields (in case log format has changed)
        if fields is None:
            self.fields = { 'ip':0,
                            'date':1,
                            'time':2 }
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
        else:
            try:
                if not all([ isinstance(fields[x],int) \
                            for x in ['ip','date','time'] ]):
                    self.__fields_error()
            except:
                self.__fields_error()


    def __fields_error(self):
        raise ValueError('''`fields` must contain a dict, with keys `ip`, `date`,
                          and `time` referencing 'integer column numbers.
                          ''')

    def parse_requests(self,requests,delimeter=','):
        """Parse SEC EDGAR log data in csv format

        Usage::

            >>> from sessionization import SessionParser
            >>> input = open('log.csv','r')
            >>> ouput = open('output.txt','w')
            >>> sp = SessionParser(output)
            >>> sp.parse_requests(input)
            >>> sp.terminate_remaining_sessions()

        :param requests: File object or generator with csv log data
        :param delimeter: Delimeter separating fields in requests (default = ',')
        """

        for line in requests:

            try:

                # split the line into arguments
                args = line.split(delimeter)

                # pick out the arguments that are needed
                uip = args[ self.fields['ip'] ]
                date = args[ self.fields['date'] ]
                time = args[ self.fields['time'] ]

                dtime = datetime.strptime(date + ' ' + time,
                                            '%Y-%m-%d %H:%M:%S')

                # Check and store time
                if self.current_time is None:
                    self.current_time = dtime
                    delta = timedelta(seconds=0)
                else:
                    delta = dtime - self.current_time
                    self.current_time = dtime

                # if the time has changed check for terminated sessions
                if delta.seconds > 0:
                    self._detect_terminated_sessions()

                # Check if user is active, and store or update as necessary
                if uip in self.active_users.keys():
                    u = self.active_users[uip]
                    u.update(self.current_time)
                else:
                    u = User(self.line_id,uip,self.current_time)
                    self.active_users.update({uip:u})

            except:
                # On failure, skip line and print warning
                warnings.warn('Skipping line '+str(self.line_id)+': failed to parse.',
                            RuntimeWarning)

            # increment unique line id
            self.line_id += 1

    def _write_session_info(self,sessions):
        """Print session information for list of Users to `output`"""

        # sort so that sessions print in the correct order
        sessions.sort(key=lambda x: (x.start_time,x.lid))

        # write to output file
        for user in sessions:
            self.output.write( user.session_info())

    def _detect_terminated_sessions(self):
        """Remove users with session length exceeding `inactivity_period` and
        output the session info.
        """

        terminated_sessions = []

        # iterate through active users
        for uip in self.active_users.keys():

            user = self.active_users[uip]

            # Check if user's session has expired
            if (self.current_time - user.latest_time).seconds > self.inactivity_period:

                # store users with terminated session
                terminated_sessions.append(user)

                # remove user from active users
                self.active_users.pop(uip)

        self._write_session_info(terminated_sessions)

    def terminate_remaining_sessions(self):
        """Remove all users and output their session info."""

        # store users with terminated session
        terminated_sessions = [ self.active_users[ip] for ip in self.active_users.keys()]

        # reset active users
        self.active_users = {}

        self._write_session_info(terminated_sessions)

class User(object):
    """Represents a user in a SEC EDGAR data log and tracks requests

    :param lid: integer line number for user's first request in a session
    :param ip: user ip address string
    :param start_time: datetime object for time of user's first request in a session
    """
    def __init__(self,lid,ip,start_time):

        # identifying information
        self.lid = lid
        self.ip = ip

        # times
        self.start_time = start_time
        self.latest_time = start_time

        self.num_docs = 1

        # check for valid ip
        try:
            ip_arr = self.ip.split('.')
            if len(ip_arr) != 4:
                self.__ip_error()
            for x in ip_arr:
                if (len(x) < 1) or (len(x) > 3):
                    self.__ip_error()
        except:
            self.__ip_error()

        # check for valid start time
        if not isinstance(start_time,datetime):
            raise ValueError('start_time must be a valid datetime object.')

        if not isinstance(lid,int):
            raise ValueError('lid must be an integer.')

    def __ip_error(self):
        raise ValueError('Invalid ip address.')

    def update(self,time):
        """Update the user with a new request

        Usage:
            >>> import sessionization
            >>> from datetime import datetime
            >>> fmt = '%Y-%m-%d %H:%M:%S'
            >>> u = sessionization.User(0,'107.23.85.jfd',
            >>>         datetime.strptime( '2017-06-30 00:00:04', fmt)
            >>> u.update(datetime.strptime( '2017-06-30 00:00:06', fmt)

        :param time: datetime object for time of user's new request
        """

        # check that time is after start time
        if time < self.start_time:
            raise ValueError('Update time must not precede start time.')

        # store the most recent time
        self.latest_time = time

        # increment the number of documents
        self.num_docs += 1


    def session_length(self):
        '''Return the users session length in seconds as an integer'''

        return 1 + (self.latest_time - self.start_time).seconds

    def session_info(self,fmt='%Y-%m-%d %H:%M:%S'):
        '''Return a string representation of the session in csv format:

            >>> ip,start_datetime,end_datetime,session_length,num_docs

        :param fmt: output format for datetime objects
        '''
        return self.ip + ',' + self.start_time.strftime(fmt) + ',' + \
               self.latest_time.strftime(fmt) + ',' + \
               str(self.session_length()) + ',' + str(self.num_docs) + '\n'


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
    parser.add_argument("-n", "--line_buffer", type=int,
                    help="number of lines to parse at a time",default=100 )
    parser.add_argument("-d", "--header", type=int,
                    help="number of header lines to skip at start of log file",default=1 )

    args = parser.parse_args()

    if args.line_buffer < 0:
        raise ValueError("line_buffer ('-n') must be a positive integer")

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

    sp = SessionParser(args.output_file,inactivity_period=inactivity_period)

    with args.log_file as f:

        # skip header lines
        for i in range(args.header):
            line = f.readline()

        while True:
            line_gen = list(islice(f, args.line_buffer))
            if not line_gen:
                break
            sp.parse_requests(line_gen)

        # clean up at end of file
        sp.terminate_remaining_sessions()


