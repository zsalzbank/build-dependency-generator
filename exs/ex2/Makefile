all: class1.o class2.o out

class1.o: class1.cpp
	g++ -c class1.cpp

class2.o: class2.cpp
	g++ -c class2.cpp

out: class1.o
	g++ main.cpp class1.o class2.o -o out

.PHONY: clean
clean:
	-rm *.o out
