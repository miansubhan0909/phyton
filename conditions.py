# if else statement
marks = int(input("Enter marks ="))
if marks >= 80:
    print("Excellent")
elif marks >= 50:
    print("Pass")
else:
    print("Fail")
# for loop
print("-- for loop start --")
for i in range(5):
    print(i)
print("-- for loop end --")#dhhjkksdkskkskskksks
#while loop
print("-- while loop start --")
count = 1
while count <=5:
    print(count)
count = count + 1
print("-- while loop end --")

#for loop with break and continue
print("-- for loop with break and continue start --")
for number in range(1, 6): #yahaan 1 se 5 tak loop chale ga

    if number == 3:# yahaan agar number 3 ho ga to yahaan loop break ho jae ga
        continue  
    if number == 5:# yahaan agar number 5 ho ga to yahaan loop break ho jae ga
        break

    print(number)
print("-- for loop with break and continue end --")

# if else statement with logical operators
print("-- if else statement with logical operators start --")
age = int(input("Enter age = "))
if age >= 18 and age <= 65:
    print("You are eligible to work.")
else:
    print("You are not eligible to work.")  

# if else with user input
print("-- if else with user input start --")
number=int(input("Enter a number = "))
if number > 0:
    print("The number is positive.")
elif number < 0:
    print("The number is negative.")
else:
    print("The number is zero.")
print("-- if else with user input end --")
