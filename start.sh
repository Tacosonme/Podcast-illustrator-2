#!/bin/bash
# Start script that uses Railway's PORT environment variable
exec gunicorn main:app --bind 0.0.0.0:$PORT
