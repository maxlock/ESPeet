#!/usr/bin/python3

# a quick test script to validate the maths

from math import atan2,sin,cos,radians,degrees

anemDuration_=16
directions_=[]

def circMean(samples_):
  cosSum_ = 0
  sinSum_ = 0
  n_ = len(samples_)
  for sample_ in samples_:
    cosSum_ += cos(radians(sample_))
    sinSum_ += sin(radians(sample_))
  return (degrees(atan2(sinSum_/n_, cosSum_/n_ )) + 360) % 360

for vaneDelay_ in range(1,16):
  print((vaneDelay_/anemDuration_)*360)
  directions_.append((vaneDelay_/anemDuration_)*360)

print("average %.0f" % circMean(directions_))
