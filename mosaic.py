#!/usr/bin/env python

import subprocess as sp
import argparse
import time

try:
    from pymediainfo import MediaInfo
except ImportError:
    print "Easy Selector! Please install mediainfo and pymediainfo first!\n\nFor example:\n\nsudo apt snstall mediainfo\nsudo pip install pymediainfo\n"
    exit(1)

try:
    import ifaddr
except ImportError:                                                                                                                                                                                                                    
    print "Blimey! Please install ifaddr!\n\nFor example:\n\nsudo pip install ifaddr\n"
    exit(1)

parser = argparse.ArgumentParser(description='Create a 3x6 mosaic from a UDP TS stream')
parser.add_argument('multicastIP', help='The input multicast address')
parser.add_argument('multicastPort', help='The input multicast port')
parser.add_argument('interfaceIP', help='The IP address of the receiving interface')
parser.add_argument('serviceNames', help='A comma sepated list of service names to display', type=lambda s: [str(item) for item in s.split(',')])
parsed_args = parser.parse_args()

print "About to start mosaic from {} from services {}..".format(parsed_args.multicastIP, ','.join(parsed_args.serviceNames))

def get_ip_from_interface(interfaceName):

    adapters = ifaddr.get_adapters()
    
    for i in adapters:
        if i.name == interfaceName:
            interfaceIP = i.ips[0].ip
        
    return interfaceIP

def capture_ts(interfaceIP, multicastIP, multicastPort):

    '''
    Use socat to send a multicast group membership request.
    Use netcat to capture some of the TS to file.
    TODO: Figure out how to do this in one socat command..
    '''

    tsFile = open('/tmp/mosaic.ts', 'w+')
    socat_proc = sp.Popen(['socat', 'STDIO', 'UDP4-DATAGRAM:239.255.255.255:9876,ip-add-membership={}:{}'.format(multicastIP,interfaceIP)])
    netcat_proc = sp.Popen(['netcat', '-l', '-u', '-p', '{}'.format(multicastPort), '{}'.format(multicastIP)], stdout=tsFile)
    time.sleep(5)
    netcat_proc.kill()
    socat_proc.kill()


def get_av_pids_from_servicesnames(serviceNames):

    '''
    Use mediainfo to grab the video and first audio pids for each service specified.
    Returns a dictionary of dictionaries like this:
    {'serviceName1': {'audio': 'xxx', 'video': 'xxx'}, 'serviceName2': {'audio': 'xxx', 'video': 'xxx'}}
    '''

    #for service in serviceNames:
    #    print service

    serviceMap = {}
    media_info = MediaInfo.parse('/tmp/mosaic.ts')
    for track in media_info.tracks:
        
        if track.track_type == 'Menu':
            
            print "Pids found:"
            print track.service_name + ' ' + track.list
            pidList = track.list.split(' / ')
            serviceMap['{}'.format(track.service_name)] = {}
            serviceMap['{}'.format(track.service_name)]['video'] = pidList[0]
            serviceMap['{}'.format(track.service_name)]['audio'] = pidList[1]

    return serviceMap
                       
def run_mosaic(interfaceIP, multicastIP, multicastPort, serviceMap, serviceNames):

    '''
    Run the most horrific ffmpeg command ever seen by man!
    Then pipe its output to ffplay
    '''

    ffmpeg_proc = sp.Popen(['ffmpeg', '-fix_sub_duration', 
        '-i', "udp://{}:{}?localaddr={}&buffer_size=10000000&fifo_size=10000000".format(multicastIP, multicastPort, interfaceIP),
        '-filter_complex',
        'color=black:size=1920x960:r=50[base];' 
        '[i:{}] setpts=PTS-STARTPTS, scale=640x480:interl=1:force_original_aspect_ratio=decrease, fps=50 [upperleft-video];' 
        '[i:{}] pan=1c|c0=c0,showvolume=r=60:b=5:t=0:v=0:w=480:h=20:f=0:o=v:p=1:ds=log:s=1:dm=0[upperleft-left-audio];' 
        '[i:{}] pan=1c|c0=c1,showvolume=r=60:b=5:t=0:v=0:w=480:h=20:f=0:o=v:p=1:ds=log:s=1:dm=0[upperleft-right-audio];'
        '[i:{}] setpts=PTS-STARTPTS, scale=640x480:interl=1:force_original_aspect_ratio=decrease, fps=50 [uppermiddle-video];'
        '[i:{}] pan=1c|c0=c0,showvolume=r=60:b=5:t=0:v=0:w=480:h=20:f=0:o=v:p=1:ds=log:s=1:dm=0[uppermiddle-left-audio];'
        '[i:{}] pan=1c|c0=c1,showvolume=r=60:b=5:t=0:v=0:w=480:h=20:f=0:o=v:p=1:ds=log:s=1:dm=0[uppermiddle-right-audio];'
        '[i:{}] setpts=PTS-STARTPTS, scale=640x480:interl=1:force_original_aspect_ratio=decrease, fps=50 [upperright-video];'
        '[i:{}] pan=1c|c0=c0,showvolume=r=60:b=5:t=0:v=0:w=480:h=20:f=0:o=v:p=1:ds=log:s=1:dm=0[upperright-left-audio];'
        '[i:{}] pan=1c|c0=c1,showvolume=r=60:b=5:t=0:v=0:w=480:h=20:f=0:o=v:p=1:ds=log:s=1:dm=0[upperright-right-audio];'
        '[i:{}] setpts=PTS-STARTPTS, scale=640x480:interl=1:force_original_aspect_ratio=decrease, fps=50 [lowerleft-video];'
        '[i:{}] pan=1c|c0=c0,showvolume=r=60:b=5:t=0:v=0:w=480:h=20:f=0:o=v:p=1:ds=log:s=1:dm=0[lowerleft-left-audio];'
        '[i:{}] pan=1c|c0=c1,showvolume=r=60:b=5:t=0:v=0:w=480:h=20:f=0:o=v:p=1:ds=log:s=1:dm=0[lowerleft-right-audio];'
        '[i:{}] setpts=PTS-STARTPTS, scale=640x480:interl=1:force_original_aspect_ratio=decrease, fps=50 [lowermiddle-video];'
        '[i:{}] pan=1c|c0=c0,showvolume=r=60:b=5:t=0:v=0:w=480:h=20:f=0:o=v:p=1:ds=log:s=1:dm=0[lowermiddle-left-audio];'
        '[i:{}] pan=1c|c0=c1,showvolume=r=60:b=5:t=0:v=0:w=480:h=20:f=0:o=v:p=1:ds=log:s=1:dm=0[lowermiddle-right-audio];'
        '[i:{}] setpts=PTS-STARTPTS, scale=640x480:interl=1:force_original_aspect_ratio=decrease, fps=50 [lowerright-video];'
        '[i:{}] pan=1c|c0=c0,showvolume=r=60:b=5:t=0:v=0:w=480:h=20:f=0:o=v:p=1:ds=log:s=1:dm=0[lowerright-left-audio];'
        '[i:{}] pan=1c|c0=c1,showvolume=r=60:b=5:t=0:v=0:w=480:h=20:f=0:o=v:p=1:ds=log:s=1:dm=0[lowerright-right-audio];'
        '[base][upperleft-video] overlay=(640-overlay_w):(480-overlay_h):shortest=0 [upperleft];'
        '[upperleft][upperleft-left-audio] overlay=shortest=0 [tmp-upperleft]; [tmp-upperleft][upperleft-right-audio] overlay=shortest=0:x=620 [upperleft0];'
        '[upperleft0] fillborders=left=1:right=1:top=1:bottom=1:mode=fixed [tmp1];'
        '[tmp1][uppermiddle-video] overlay=(1280-overlay_w):(480-overlay_h):shortest=0 [uppermiddle];'
        '[uppermiddle][uppermiddle-left-audio] overlay=shortest=0:x=640 [tmp-uppermiddle];' 
        '[tmp-uppermiddle][uppermiddle-right-audio] overlay=shortest=0:x=1260 [uppermiddle0];' 
        '[uppermiddle0] fillborders=left=1:right=1:top=1:bottom=1:mode=fixed [tmp2];' 
        '[tmp2][upperright-video] overlay=(1920-overlay_w):(480-overlay_h):shortest=0 [upperright];' 
        '[upperright][upperright-left-audio] overlay=shortest=0:x=1280 [tmp-upperright];' 
        '[tmp-upperright][upperright-right-audio] overlay=shortest=0:x=1900 [upperright0];' 
        '[upperright0] fillborders=left=1:right=1:top=1:bottom=1:mode=fixed [tmp3];' 
        '[tmp3][lowerleft-video] overlay=(640-overlay_w):(960-overlay_h):shortest=0 [lowerleft];' 
        '[lowerleft][lowerleft-left-audio] overlay=shortest=0:y=480 [tmp-lowerleft];'
        '[tmp-lowerleft][lowerleft-right-audio] overlay=shortest=0:x=620:y=480 [lowerleft0];' 
        '[lowerleft0] fillborders=left=1:right=1:top=1:bottom=1:mode=fixed [tmp4];' 
        '[tmp4][lowermiddle-video] overlay=(1280-overlay_w):(960-overlay_h):shortest=0 [lowermiddle];'
        '[lowermiddle][lowermiddle-left-audio] overlay=shortest=0:x=640:y=480 [tmp-lowermiddle];' 
        '[tmp-lowermiddle][lowermiddle-right-audio] overlay=shortest=0:x=1260:y=480 [lowermiddle0];' 
        '[lowermiddle0] fillborders=left=1:right=1:top=1:bottom=1:mode=fixed [tmp5];' 
        '[tmp5][lowerright-video] overlay=(1920-overlay_w):(960-overlay_h):shortest=0 [lowerright];' 
        '[lowerright][lowerright-left-audio] overlay=shortest=0:x=1280:y=480 [tmp-lowerright];' 
        '[tmp-lowerright][lowerright-right-audio] overlay=shortest=0:x=1900:y=480 [lowerright0];' 
        '[lowerright0] fillborders=left=1:right=1:top=1:bottom=1:mode=fixed [tmp6];' 
        '[tmp6] yadif'.format(serviceMap[serviceNames[0]]['video'], serviceMap[serviceNames[0]]['audio'], serviceMap[serviceNames[0]]['audio'],
                              serviceMap[serviceNames[1]]['video'], serviceMap[serviceNames[1]]['audio'], serviceMap[serviceNames[1]]['audio'],
                              serviceMap[serviceNames[2]]['video'], serviceMap[serviceNames[2]]['audio'], serviceMap[serviceNames[2]]['audio'],
                              serviceMap[serviceNames[3]]['video'], serviceMap[serviceNames[3]]['audio'], serviceMap[serviceNames[3]]['audio'],
                              serviceMap[serviceNames[4]]['video'], serviceMap[serviceNames[4]]['audio'], serviceMap[serviceNames[4]]['audio'],
                              serviceMap[serviceNames[5]]['video'], serviceMap[serviceNames[5]]['audio'], serviceMap[serviceNames[5]]['audio']),
        '-r', '50', 
        '-an', '-sn', 
        '-c:v', 'rawvideo', 
        '-pix_fmt', 'yuv420p', 
        '-f', 'nut', '-'], stdout=sp.PIPE)

    ffplay_proc = sp.Popen(['ffplay', '-i', '-'], stdin=ffmpeg_proc.stdout)



    




capture_ts(parsed_args.interfaceIP, parsed_args.multicastIP, parsed_args.multicastPort)

servicePids = get_av_pids_from_servicesnames(parsed_args.serviceNames)

print servicePids

run_mosaic(parsed_args.interfaceIP, parsed_args.multicastIP, parsed_args.multicastPort, servicePids, parsed_args.serviceNames)
