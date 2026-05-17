n=int(input())
ans=[]
for k in range(n):
    N=int(input())
    sum=0
    days=0
    li=[]
    for kk in range(N):
        l=list(map(int,input().split()))
        l.append(kk+1)
        li.append(l)
    #print(li[2][1])
    max=0
    for j in range(N):
        print(*li)
        for i in range(N-j):
            if max<(li[i][0]+days)*li[i][1]:
                max=(li[i][0]+days)*li[i][1]
                maxi=i
        ans.append(li[maxi][2])
        li.pop(maxi)
        max=0
    print(*ans)