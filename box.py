#"""Raspberry Pi Face Recognition Treasure Box
#Treasure Box Script
#Copyright 2013 Tony DiCola 
#"""
import cv2
import config
import face
import hardware
from sqlalchemy import create_engine, text
import pandas as pd
import pigpio
import RPi.GPIO as GPIO
import time
import datetime
import random

GPIO.setmode(GPIO.BCM)

GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP)
#GPIO.setup(22, GPIO.OUT)
pi = pigpio.pi()
#p = GPIO.PWM(22, 50)
#p.start(7.5)

def log(user_id, confidence, motor, engine, crop):
		
	if engine.dialect.has_table(engine, 'activity'):
		sql = text('SELECT activity_id FROM activity ORDER BY created_at DESC LIMIT 1')
		result = engine.execute(sql)	
		l = []
		for thing in result:
			l.append(thing)
		activity_id = l[0]['activity_id'] + 1
	
	else:
		activity_id = 1000

	row = [(activity_id, user_id, confidence, motor, datetime.datetime.now())]
        df = pd.DataFrame.from_records(row, columns = ['activity_id', 'user_id', 'confidence', 'motor',  'created_at'])
        df.to_sql('activity', engine, if_exists = 'append')
	file_name_path = 'debug_images/' + str(activity_id) + '.png'
	cv2.imwrite(file_name_path, crop)

	
def dispense(name, user_id, confidence, engine, crop):
        print 'Dispensing for ' + name
	
	if random.uniform(0, 1.0) < 1:
		#for i in range(1, 5):
                #        pi.set_servo_pulsewidth(22, 500)
                #        time.sleep(.05)
                #        pi.set_servo_pulsewidth(22, 2000)
                #        time.sleep(.05)

                pi.set_servo_pulsewidth(17, 1400)
                time.sleep(0.5)
                pi.set_servo_pulsewidth(17, 1000)
		log(user_id, confidence, 1, engine, crop)

        else:
		for i in range(1, 5):
                        pi.set_servo_pulsewidth(22, 500)
                        time.sleep(.05)
                        pi.set_servo_pulsewidth(22, 2000)
                        time.sleep(.05)
                pi.set_servo_pulsewidth(27, 1000)
                time.sleep(0.5)
                pi.set_servo_pulsewidth(27, 0)
		log(user_id, confidence, 1, engine, crop)

	#pi.set_servo_pulsewidth(17, 0)
	#pi.set_servo_pulsewidth(27, 0)
	
def is_button_pressed():
	input_state = GPIO.input(5) and GPIO.input(18)
	pi.write(5, 1)
	pi.write(18, 1)
	return input_state

def standby_lights(i):
	if i:
		pi.write(23, 1)
		pi.write(24, 0)
	else:
		pi.write(23, 0)
		pi.write(24, 1)

if __name__ == '__main__':
	# Load training data into model
	print 'Loading training data...'
	model = cv2.createEigenFaceRecognizer()
	model.load(config.TRAINING_FILE)
	print 'Training data loaded!'
	
	# Initialize camer and box.
	camera = config.get_camera()
	
	# read in users lookup table
	engine = create_engine('postgresql://root@localhost:5432/pi')
	users = pd.read_sql('users', engine)
	
	i = True
	while True:
		try:
			image = camera.read()
			# Convert image to grayscale.
			image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
		
			# Get coordinates of single face in captured image.
			faces = face.detect_face(image, single = False)
			#faces = None
			#standby_lights(i)
			pi.write(23, 0)
			pi.write(24, 0)
			
			if faces is not None:
				image_copy = image.copy()
				for (x, y, w, h) in faces:
                               		cv2.rectangle(image, (x, y), (x+w, y+h), (255, 255, 0))
				
				#smiles = face.detect_smile(image, single = False)
				#if smiles is not None:
				#	for (x, y, w, h) in smiles:
                                #        	cv2.rectangle(image, (x, y), (x+w, y+h), (255, 255, 0))



			if faces is not None:
				pi.write(23, 1)
				pi.write(24, 1)
				for facez in faces:
					x, y, w, h = facez
					
					## Crop and resize image to face.
					crop = face.resize(face.crop(image_copy, x, y, w, h))
					
					## Test face against model.
					user_id, confidence = model.predict(crop)
				
					name = users['name'].loc[users['user_id'] == user_id]
					
					name = str(name)
					#print name.at[0,1]
					cv2.rectangle(image, (x, y), (x+w, y+h), (255, 255, 0))
					cv2.putText(image, name, (x, y+h+20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 2)
				
					
					if not is_button_pressed():
						#log(engine, user_id, confidence)
						dispense(name, user_id, confidence, engine, crop)
						

					print name
					print confidence
				
                	cv2.imshow('Frame', image)
                	cv2.waitKey(1) & 0xFF
			
			i =  not i

		except KeyboardInterrupt:
			pi.stop()
			GPIO.cleanup()

	
		#print 'Predicted {0} face with confidence {1} (lower is more confident).'.format(
		#	'POSITIVE' if label == config.POSITIVE_LABEL else 'NEGATIVE', 
		#	confidence)
		#if label == config.POSITIVE_LABEL and confidence < config.POSITIVE_THRESHOLD:
		#	print 'Recognized face!'
		#	box.unlock()
		#else:
		#	print 'Did not recognize face!'
