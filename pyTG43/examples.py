import pyTG43
import pydicom

rp = pydicom.dcmread('examples/HDR/RP.HDR.dcm')
rs = pydicom.dcmread('examples/HDR/RS.HDR.dcm')

print('-'*40)
print(' Eclipse (HDR)')
print('-'*40)
pyTG43.tpsComp(rp, rs, 'examples/HDR/')

rp = pydicom.dcmread('examples/PDR/RP.PDR.dcm')
rs = pydicom.dcmread('examples/PDR/RS.PDR.dcm')

print('-'*40)
print(' Eclipse (PDR)')
print('-'*40)
pyTG43.tpsComp(rp, rs, 'examples/PDR/')

# rp = pydicom.dcmread('examples/rotated/RP.dcm')
# rs = pydicom.dcmread('examples/rotated/RS.dcm')
#
# print('-'*40)
# print(' Eclipse (rotated)')
# print('-'*40)
# pyTG43.tpsComp(rp, rs, 'examples/rotated/')