#!/usr/bin/env python

import sys, os
import decimal

senderPayPalMoneyMarket = 'PayPal - Money Market'
senderBankAccount = 'Bank Account'
taggerCustomers = ("2ManyRobots",
                   "Mathias Kunter")
taggerAccount = "Income - Affiliate - Tagger"

expenseAccountPayPal = 2
expenseAccounts = ("Expense - Hosting - DWNI",
                   "Expense - Hosting - CCCP",
                   "Expense - Bank - PayPal",
                   "Expense - Hardware",
                   "Expense - Development",
                   "Expense - Marketing",
                   "Expense - Internet",
                   "Expense - Travel",
                   "Expense - Supplies",
                   "Expense - Gifts",
                   "Expense - Events",
                   "Expense - Software",
                   "Expense - Community Management",
                   "Income - Donations - PayPal") 

incomeAccountDonation = 0
incomeAccountInterest = 1
incomeAccounts = ("Income - Donations - PayPal", 
                  "Income - Bank - Interest",
                  "Income - Licenses - Live Data F",
                  "Expense - Hardware",
                  "Expense - Gifts",
                  "Expense - Marketing",
                  "Expense - Internet",
                  "Expense - Travel",
                  "Expense - Software",
                  "Expense - Bank - PayPal",
                 )


bankAccountHOB = 0
bankAccountPayPal = 1
bankAccounts = ("Account - Bank - MCB Checking", 
                "Account - Bank - PayPal")

def selectExpenseAccount():
    index = 1
    print "0) Skip this transaction"
    for acc in expenseAccounts:
        print "%d) %s" % (index, acc)
        index += 1

    while True:
        x = None
        try:
            x = int(raw_input("select account> "))
        except ValueError:
            print "Invalid selection"
            continue

        x -= 1
        if x >= -1 and x < len(expenseAccounts):
            break

    return x

def selectIncomeAccount():
    index = 1
    print "0) Skip this transaction"
    for acc in incomeAccounts:
        print "%d) %s" % (index, acc)
        index += 1

    while True:
        x = None
        try:
            x = int(raw_input("select account> "))
        except ValueError:
            print "Invalid selection"
            continue

        x -= 1
        if x >= -1 and x < len(incomeAccounts):
            break

    return x

def toFloat(svalue):
    return float(svalue.replace(",", ""))
                  
def income(data, out, gross):
    '''called when we have income to write'''

    if data['Type'].find('Payment') == -1 and \
       data['Type'].find('Dividend') == -1 and \
       data['Type'].find('Update') == -1:
        print "Received some other type of credit: %s, %s, %.2f, %s" % (data['Date'], data['Name'], gross, data['Type'])
        print "Which account should be credited:"
        x = selectIncomeAccount()
        if x == -1: return
        account = incomeAccounts[x] 
        out.write('TRNS\t"%s"\t"Account - Bank - PayPal"\t"%s"\t"%s"\t%s\t"%s"\n' % (data['Date'], data['Name'], data['Type'], data['Net'], data['Item Title']))
        out.write('SPL\t"%s"\t"%s"\t"%s"\t%.2f\n' % (data['Date'], account, data['Name'], -gross))
        # Print out the Fee SPL, if any
        if data["Fee"] and toFloat(data["Fee"]) < 0.0:
            account = expenseAccounts[expenseAccountPayPal]
            fee = abs(toFloat(data["Fee"]))
            out.write('SPL\t"%s"\t"%s"\tFee\t%.2f\n' % (data['Date'], account, fee))
        out.write('ENDTRNS\n')
        return

    if data['Name'] == senderPayPalMoneyMarket:
        account = incomeAccounts[incomeAccountInterest]
    elif data['Name'] in taggerCustomers:
        account = taggerAccount
    else:
        account = incomeAccounts[incomeAccountDonation]

    out.write('TRNS\t"%s"\t"Account - Bank - PayPal"\t"%s"\t"%s"\t%s\t"%s"\n' % (data['Date'], data['Name'], data['Type'], data['Net'], data['Item Title']))
    out.write('SPL\t"%s"\t"%s"\t"%s"\t%.2f\n' % (data['Date'], account, data['Name'], -gross))

    # Print out the Fee SPL, if any
    if data["Fee"] and toFloat(data["Fee"]) < 0.0:
        account = expenseAccounts[expenseAccountPayPal]
        fee = abs(toFloat(data["Fee"]))
        out.write('SPL\t"%s"\t"%s"\tFee\t%.2f\n' % (data['Date'], account, fee))

    out.write('ENDTRNS\n')

def expense(data, out, gross):
    '''called when we have an expense to write'''

    if data['Name'] == senderBankAccount:
        account = bankAccounts[bankAccountHOB]  
    else:
        print "Received some other type of debit: %s, %s, %.2f, %s" % (data['Date'], data['Name'], gross, data['Type'])
        print "Which account should be debited:"
        x = selectExpenseAccount()
        if x == -1: return
        account = expenseAccounts[x] 
    
    out.write('TRNS\t"%s"\t"Account - Bank - PayPal"\t"%s"\t"%s"\t%s\t"%s"\n' % (data['Date'], data['Name'], data['Type'], data['Net'], data['Item Title']))
    out.write('SPL\t"%s"\t"%s"\t"%s"\t%.2f\n' % (data['Date'], account, data['Name'], abs(gross)))

    # Print out the Fee SPL, if any
    if toFloat(data["Fee"]) < 0.0:
        print "**** negative fee!"
    if data["Fee"]:
        account = expenseAccounts[expenseAccountPayPal]
        fee = toFloat(data["Fee"]) * -1
        #if toFloat(data["Fee"]) > 0.0:
        out.write('SPL\t"%s"\t"%s"\tFee\t%.2f\n' % (data['Date'], account, fee))

    out.write('ENDTRNS\n')

def get_ref_transactions(transactions, id):
    trans = []
    for tran in transactions:
        if tran['Reference Txn ID'] ==  id: trans.append(tran)

    return trans

def remove_transaction(transactions, id):
    index = 0
    for tran in transactions:
        if tran['Transaction ID'] ==  id: 
            del transactions[index]
            break
        index += 1

    return transactions

def update_transaction(transactions, update):
    index = 0
    for tran in transactions:
        if tran['Transaction ID'] ==  update['Transaction ID']: 
            transactions[index] = update
            break
        index += 1

    return transactions

def currency_conversion(transactions):
    '''
    Find, combine and convert EUR transactions to US dollars so that quickbooks doesn't have to know about them.
    '''
 
    cont = True
    while cont:
        cont = False
        index = 0
        for tran in transactions:
            # Find the base transaction
            if tran['Currency'] in ["EUR", "GBP"] and tran['Type'] != 'Currency Conversion':

                # Get the dependent transactions -- the ones that give the info on the currency conversion
                depTransactions = get_ref_transactions(transactions, tran['Transaction ID'])
                assert len(depTransactions) == 2, "Too many dependent currency conversion transactions found"

                eurAmount = ""
                if depTransactions[0]['Currency'] in ["EUR", "GBP"]:
                    eurAmount = depTransactions[0]['Gross']
                elif depTransactions[1]['Currency'] in ["EUR", "GBP"]:
                    eurAmount = depTransactions[1]['Gross']
                else:
                    assert 0, "Cannot find EUR value"

                usdAmount = ""
                if depTransactions[0]['Currency'] == 'USD':
                    usdAmount = depTransactions[0]['Gross'].strip()
                elif depTransactions[1]['Currency'] == 'USD':
                    usdAmount = depTransactions[1]['Gross'].strip()
                else:
                    assert 0, "Cannot find USD value"

                # Remove any commas from the inputs
                usdAmount = usdAmount.replace(',', '')
                eurAmount = eurAmount.replace(',', '')

                twoPlaces = decimal.Decimal('0.01')
                tenPlaces = decimal.Decimal('0.0000000001')

                con = decimal.Context(prec=28, rounding=decimal.ROUND_HALF_UP)
                eurAmount = con.abs(decimal.Decimal(eurAmount, con))
                usdAmount = con.abs(decimal.Decimal(usdAmount, con))
                ratio = con.divide(eurAmount, usdAmount)

                tran['Fee'] = str(con.minus(con.divide(con.abs(decimal.Decimal(tran['Fee'].replace(',', ''), con)), ratio)).quantize(twoPlaces))
                tran['Gross'] = str(con.divide(con.abs(decimal.Decimal(tran['Gross'].replace(',', ''), con)), ratio).quantize(twoPlaces))
                tran['Net'] = str(con.divide(con.abs(decimal.Decimal(tran['Net'].replace(',', ''), con)), ratio).quantize(twoPlaces))
                tran['Currency'] = 'USD';

                #print "Fee: %s" % tran['Fee']
                #print "Gross: %s" % tran['Gross']
                #print "Net: %s vs %s" % (tran['Net'], str(usdAmount.quantize(twoPlaces)))

                assert tran['Net'] != usdAmount, "Converted amount does not match PayPal's amount"

                # Put the updated transaction into the list of transactions
                transactions = update_transaction(transactions, tran)

                # Remove the two conversion transactions
                for t in depTransactions:
                    transactions = remove_transaction(transactions, t['Transaction ID'])

                cont = True
                break

fp = None
try:
    fp = open(sys.argv[1], "r")
except IOError:
    print "Cannot open input file %s" % sys.argv[1]
    exit(0)

out = None
try:
    out = open(sys.argv[2], "w")
except IOError:
    print "Cannot open output file %s" % sys.argv[2]
    exit(0)

header = fp.readline()
headerCols = [ x.strip() for x in header.split('\t') ]

out.write('!TRNS\tDATE\tACCNT\tNAME\tCLASS\tAMOUNT\tMEMO\n')
out.write('!SPL\tDATE\tACCNT\tNAME\tAMOUNT\tMEMO\n')
out.write('!ENDTRNS\n')

trans = []
for line in fp.readlines():
    cols = line.split('\t')
    index = 0
    data = {}
    for col in cols:
        if col[0] == '"': col = col[1:len(col) - 1]
        try:
            data[headerCols[index]] = col
        except IndexError:
            pass
           
        index += 1

    trans.append(data)

currency_conversion(trans)
trans.reverse()

# Ignore temprary hold placed, but not removed

prevBalance = ""
for data in trans:

    if prevBalance == data['Balance']:
        print "** Skipping non balance affecting: %s - %s - %s" % (data['Name'], data['Gross'], data['Status'])
        continue
    prevBalance= data['Balance'];

    # Skip over bogus 1 cent transactions
    if data['Currency'] == 'USD' and data['Gross'] == '0.01':
        print "** Skipping bogus: %s - %s - %s" % (data['Name'], data['Gross'], data['Status'])
        continue

    # Skip over pending transactions
    if data['Status'] in ['Pending', 'Uncleared']: 
        print "** Skipping pending: %s - %s - %s" % (data['Name'], data['Gross'], data['Status'])
        continue

    # Skip over reversed transactions
#    if data['Status'] == 'Completed' and data['Type'] == 'Reversal':
#        print "** Skipping reversed: %s - %s - %s" % (data['Name'], data['Gross'], data['Status'])
#        continue

    gross = toFloat(data['Gross'])
    if gross > 0.0:
        income(data, out, gross)
    else:
        expense(data, out, gross)

fp.close()
out.close()

