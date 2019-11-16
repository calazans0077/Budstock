from flask import Flask, render_template, url_for, flash, redirect, request, make_response
import sqlite3
from datetime import datetime
from fpdf import FPDF, HTMLMixin
from collections import OrderedDict

class MyFPDF(FPDF, HTMLMixin):
    #Necessário para a conversao de html para pdf
    pass

conn = sqlite3.connect('teste.db', check_same_thread=False)
conn.execute("PRAGMA foreign_keys = 1")
c = conn.cursor()

#Cria a tabela com os estoques
#Tabela principal
c.execute("""CREATE TABLE IF NOT EXISTS Estoques(
    codEstoque INTEGER PRIMARY KEY NOT NULL,
    nome TEXT NOT NULL
)""")

conn.commit()

#Cria a tabela para as Sessões (Relação 1 para N)
#As linhas guardam os dados referentes a sessão de cada estoque
#Cada estoque pode ter somente 1 sessão ativa
#As sessões são mantidas até esta ser encerrada pelo usuário
#Ao deletar o estoque, a sessão ativa é deletada da tabela de Sessões
c.execute("""CREATE TABLE IF NOT EXISTS Sessoes(
            receita REAL NOT NULL,
            hora_ini TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            estoque INTEGER NOT NULL,
            FOREIGN KEY (estoque) REFERENCES Estoques(codEstoque) ON DELETE CASCADE
            )""")

conn.commit()

#Cria a tabela para os arquivos html dos relatorios (Relação 1 para N)
#Uma tabela para todos os relatórios
#Funciona de forma similar a tabela de Sessões
c.execute("""CREATE TABLE IF NOT EXISTS Relatorios(
            hora_ini TEXT NOT NULL,
            rel_html BLOB NOT NULL,
            estoque INTEGER NOT NULL,
            FOREIGN KEY (estoque) REFERENCES Estoques(codEstoque) ON DELETE CASCADE
            )""")

conn.commit()




class Estoque:
    # 1 ATRIBUTO ; 1 METODOS

    def __init__(self, estoque):
        # estoque = nome do estoque;
        self.estoque = estoque

    def criar_tabela(self):
        # Insere o estoque no banco de dados e cria uma tabela correspondente
        # Não é possível inserir o estoque se o nome já estiver ocupado
        c.execute("SELECT * FROM Estoques WHERE nome=?", (self.estoque,))
        check = c.fetchone()
        if not check and self.estoque:
            with conn:
                c.execute("INSERT INTO Estoques (nome) VALUES (?)", (self.estoque,))
            with conn:
                c.execute("""CREATE TABLE IF NOT EXISTS [""" + self.estoque + """](
            numero INTEGER NOT NULL,
            nome TEXT NOT NULL,
            preço REAL NOT NULL,
            quantidade INTEGER NOT NULL,
            estoque INTEGER NOT NULL,
            FOREIGN KEY (estoque) REFERENCES Estoques(codEstoque) ON DELETE CASCADE
            )""")

    @staticmethod
    def remover_estoque(nome_estoque):
        # Recebe o nome do estoque
        # Remove o estoque do Banco e os produtos contidos nesse estoque
        with conn:
            c.execute("DELETE FROM Estoques WHERE nome=?", (nome_estoque,))
        with conn:
            c.execute("DROP TABLE IF EXISTS ["+nome_estoque+"]")

    @staticmethod
    def alterar_estoque(estoque_antigo, estoque_novo):
        # Altera o nome do estoque
        c.execute("SELECT * FROM Estoques WHERE nome=?", (estoque_novo,))
        check = c.fetchone()
        if not check and estoque_novo:
            c.execute("UPDATE Estoques SET nome=?  WHERE nome=?",(estoque_novo, estoque_antigo))
            c.execute("ALTER TABLE [" + estoque_antigo + "] RENAME TO [" + estoque_novo + "]")
            conn.commit()
            return True
        return False
        

    def mostrar_estoque(self):
        # Retorna uma lista dos produtos dentro do estoque
        with conn:
            c.execute("SELECT numero,nome,preço,quantidade FROM [" +self.estoque+ "] ORDER BY numero")
        return (c.fetchall())

    @staticmethod
    def gerar_li_li_tup(estoque):
        # Função para criar os nomes ( começando por 0) das informações para o request_form
        prod = str(estoque.mostrar_estoque()).translate({ord(c): '' for c in "[]()'"})
        prod = list(prod.split(","))

        li_li_tup = []
        y = []
        s = ["numero", "nome", "preço", "quantidade"]
        z = 0
        k = 0
        for info in prod:
            j = str(k)
            tup = (s[z] + j, info)
            y.append(tup)
            if z == 3:
                k = k + 1
                li_li_tup.append(y)
                y = []
            z = (z + 1) % 4
        return li_li_tup

    @staticmethod
    def mostrar_estoques():
        # Para testes: printa os estoques no banco
        c.execute("SELECT * FROM Estoques")
        return c.fetchall()

    @staticmethod
    def get_estoque_nome(estoque_num):
        # Para testes: printa os estoques no banco
        c.execute("SELECT nome FROM Estoques WHERE codEstoque=?",(estoque_num,))
        lista = c.fetchone()
        return lista[0]

    @staticmethod
    def cod_estoque(nome):
        # retorna a chave do estoque
        c.execute("SELECT * FROM Estoques WHERE nome = ?", ( nome,))
        lista = c.fetchone()
        return lista[0]

class Produto:
    # 5 ATRIBUTOS; 3 METODOS

    def __init__(self, numero, nome, preço, quantidade, estoque_nome):

        # O ultimo atributo recebe o nome do estoque ao qual o produto pertence
        self.numero = numero
        self.nome = nome
        self.preço = preço
        self.quantidade = quantidade
        self.estoque_nome = estoque_nome

    def produto_novo(self):

        # Insere o produto na tabela correspondente ao seu estoque
        # Caso o Numero OU o Nome já estejam ocupados, o metodo não insere o produto
        if self.numero  and self.nome and self.preço and self.quantidade:
            try:
                int(self.numero)
                float(self.preço)
                int(self.quantidade)
                c.execute("SELECT * FROM [" + self.estoque_nome + "] WHERE nome=? OR numero=? ", (self.nome, self.numero))
                check = c.fetchone()
                if not check:
                    if int(self.quantidade) >= 0:
                        c.execute("SELECT * FROM Estoques WHERE nome = ?", (self.estoque_nome,))
                        lista = c.fetchone()
                        c.execute("INSERT INTO [" + self.estoque_nome + "] VALUES (?, ?, ?, ?, ?)", (self.numero, self.nome,self.preço, self.quantidade,lista[0]))
                        conn.commit()
            except Exception as inst:
                print (inst)
                pass

    def alterar_produto(self, nro_prod):

        # Atualiza todas as informações do produto com o Numero equivalente a "nro_prod"
        # Metodo criado a fim do objeto utilizado possuir 1 ou mais atributos a serem atualizados
        # Caso o Numero OU o Nome já estejam ocupados, o metodo não atualiza o produto
        # c.execute("SELECT * FROM "+self.estoque_nome+" WHERE nome=? OR numero=? ",(self.nome,self.numero))
        if self.numero  and self.nome and self.preço and self.quantidade:
            try:
                int(self.numero)
                float(self.preço)
                int(self.quantidade)
                c.execute("SELECT * FROM [" + self.estoque_nome + "] WHERE numero=? ", (self.numero,))
                check = c.fetchone()
                if not check or int(self.numero) == int(nro_prod):
                    c.execute("SELECT * FROM [" + self.estoque_nome + "] WHERE nome=? ", (self.nome,))
                    check = c.fetchone()
                    if not check or check[0] == nro_prod:
                        if int(self.quantidade) >= 0 :
                            c.execute(
                                "UPDATE [" + self.estoque_nome + "] SET numero=?, nome=?, preço=?, quantidade=?  WHERE numero=?",
                                (self.numero, self.nome, self.preço, self.quantidade, nro_prod))
                            conn.commit()
            except Exception as inst:
                print (inst)
                pass

    def remover_produto(self):

        # Remove o produto de sua tabela/estoque correspondente
        with conn:
            c.execute("DELETE FROM [" + self.estoque_nome + "] WHERE numero=?", (self.numero,))

class Sessao:

    def __init__(self, estoque_nome, hora_ini, receita = 0, hora_fim = "0/0/0", ):
        self.receita = receita
        self.hora_ini = hora_ini
        self.hora_fim = hora_fim
        self.estoque_nome = estoque_nome

    def sessao_nova (self):
        # Insere a sessão na tabela de sessões e cria uma tabela para os produtos vendidos
        # Se a sessão nao foi encerrada, os dados antigos permanecerão
        cod = Estoque.cod_estoque(self.estoque_nome)
        c.execute("SELECT * FROM Sessoes WHERE estoque=? ", (cod,))
        check = c.fetchone()
        if not check:
            with conn:
                c.execute("INSERT INTO Sessoes VALUES (?, ?, ?, ?)", ( self.receita, self.hora_ini, 
                                                                  self.hora_fim, cod))
        with conn:
            c.execute("""CREATE TABLE IF NOT EXISTS [""" + self.estoque_nome + """_vendidos](
                numero INTEGER NOT NULL,
                nome TEXT NOT NULL,
                preço REAL NOT NULL,
                quantidade INTEGER NOT NULL
                )""")

    @staticmethod
    def adicionar_receita (estoque, valor):
        #Adiciona o valor do subtotal de um carrinho confirmado
        cod = Estoque.cod_estoque(estoque)
        c.execute("SELECT receita FROM Sessoes WHERE estoque=? ", ( cod,))
        check = c.fetchone()
        x = check[0]
        x = x + valor
        c.execute("UPDATE Sessoes SET receita=? WHERE estoque=?",( x, cod))
        conn.commit()
    
    @staticmethod
    def adicionar_hora_fim (estoque, hora):
        #Insere a hora em que a sessão é encerrada
        c.execute("UPDATE Sessoes SET hora_fim=? WHERE estoque=?",( hora, Estoque.cod_estoque(estoque)))
        conn.commit()

    @staticmethod
    def get_vendidos (estoque):
        #Coleta todos os produtos vendidos durante a sessão 
        c.execute("SELECT * FROM [" + estoque + "_vendidos] ORDER BY numero ")
        check = c.fetchall()
        return check

    @staticmethod
    def get_sessao (estoque):
        #Coleta os dados referentes a sessão
        c.execute("SELECT receita,hora_ini,hora_fim FROM Sessoes WHERE estoque=? ",(Estoque.cod_estoque(estoque),))
        check = c.fetchall()
        return check[0]


    @staticmethod
    def fechar_sessao (estoque):
        #Deleta a linha  correspondente a sessão da tabela Sessões e deleta a tabela utilizada para manter
        #os produtos vendidos na sessão.
        #Dessa forma, quando o aplicativo é fechado durante uma sessão, os dados da sessão não são perdidos.
        with conn:
            c.execute("DELETE FROM Sessoes WHERE estoque=?", (Estoque.cod_estoque(estoque),))
        with conn:
            c.execute("DROP TABLE  ["+ estoque +"_vendidos]")

class Prod_Vendido:

    def __init__(self, numero, nome, quantidade, preço, estoque_nome):
            self.numero = numero
            self.nome = nome
            self.quantidade = quantidade
            self.preço = preço
            self.estoque_nome = estoque_nome

    
    def vendido(self):
        #Inseri os produtos do carrinho à tabela de produtos vendidos,
        # conferindo se o produto já existe ou não nessa tabela
        # Retira do estoque a quantidade vendida do produto 
        c.execute("SELECT numero FROM [" + self.estoque_nome + "_vendidos] WHERE numero=? ",
                                                             (self.numero,))
        check = c.fetchone()
        if check:
            c.execute("SELECT quantidade FROM [" + self.estoque_nome + "_vendidos] WHERE numero=? ", 
                                                                    (self.numero,))
            check = c.fetchone()
            x = check[0]
            x = x + int(self.quantidade)
            c.execute("UPDATE [" + self.estoque_nome + "_vendidos] SET quantidade=?  WHERE numero=?",
                                                                    ( x, self.numero))
            conn.commit()
        else:
            c.execute("INSERT INTO [" + self.estoque_nome + "_vendidos] VALUES (?, ?, ?, ?)", (self.numero, self.nome,
                                                                                           self.preço, self.quantidade))
            conn.commit()
        c.execute("SELECT quantidade FROM [" + self.estoque_nome + "] WHERE numero=? ",
                                                             (self.numero,))
        check = c.fetchone()
        x = check[0]
        x = x - int(self.quantidade)
        c.execute("UPDATE [" + self.estoque_nome + "] SET quantidade=?  WHERE numero=?",
                                                                    ( x, self.numero))
        conn.commit()

class Relatorio:

    @staticmethod
    def guardar (estoque, hora_ini, html):
        #Guarda o arquivo html no banco
        cod = Estoque.cod_estoque(estoque)
        c.execute("INSERT INTO Relatorios VALUES (?, ?, ?)", (hora_ini, html, cod))
        conn.commit()

    @staticmethod
    def get_list (estoque):
        #Coleta a lista de relatorios guardados para o estoque correspondente
        cod = Estoque.cod_estoque(estoque)
        c.execute("SELECT hora_ini FROM Relatorios WHERE estoque = ? ORDER BY hora_ini DESC", ( cod,))
        return (c.fetchall())

    @staticmethod
    def get_rel (estoque, hora_ini):
        #Retorna o arquivo html do relatorio com a hora de inicio de sessao correspondente
        cod = Estoque.cod_estoque(estoque)
        c.execute("SELECT rel_html FROM Relatorios WHERE estoque = ? AND hora_ini = ?", ( cod, hora_ini))
        lista = c.fetchone()
        return lista[0]

    @staticmethod
    def del_rel (estoque, hora_ini):
        #Retira o relatório com a hora_ini dada da tabela de relatorios
        cod = Estoque.cod_estoque(estoque)
        c.execute("DELETE FROM Relatorios WHERE estoque=? AND hora_ini = ?", (cod, hora_ini))
        conn.commit()







app = Flask(__name__)


@app.route("/", methods=['GET', 'POST'])
def teste():
    repeat = Estoque.mostrar_estoques()
    tam = len(repeat)
    if request.method == "POST":
        #Confere se algum estoque foi deletado e deleta
        for i in range(tam):
            repeat[i]
            for re in repeat:    
                if str(re[1]) in request.form:
                    estoque = re[1]
                    Estoque.remover_estoque(str(estoque))
        #Confere se algum estoque foi adicionado e adiciona
        if "add" in request.form:
            stock = Estoque(request.form.get('novo_estoque'))
            Estoque.criar_tabela(stock)
    
    lista = []
    repeat = Estoque.mostrar_estoques()
    for re in repeat:
        lista.append(re[1])
    return render_template('home.html', len=len(lista), repeat=lista)


@app.route("/estoque", methods=['GET', 'POST'])
def pag_estoque():
    # Metodos Get e Post para manter o nome do estoque na pagina
    if request.method == "GET":
        estoque_info = request.args.get('info')
    elif request.method == "POST":
        estoque_info = request.form["nome_estoque"]
    estoque = Estoque(estoque_info)
    estoque.criar_tabela()
    # Checando de o Botão " Vendas" foi pressionado
    if "vendas" in request.form:
        return redirect(url_for('pag_vendas',info=estoque.estoque))
    if "relatorios" in request.form:
        return redirect(url_for('pag_relatorios',info=estoque.estoque))
    if "n_estoque" in request.form:
        novo_estoque = request.form["novo_estoque"]
        antigo_estoque = estoque_info
        con = Estoque.alterar_estoque(antigo_estoque,novo_estoque)
        if con:
            estoque = Estoque(novo_estoque)
            li_li_tup = Estoque.gerar_li_li_tup(estoque)
            return render_template('estoque.html', li_li_tup=li_li_tup, estoque=estoque.estoque)
        else:
            li_li_tup = Estoque.gerar_li_li_tup(estoque)
            return render_template('estoque.html', li_li_tup=li_li_tup, estoque=estoque.estoque)

    if request.method == "POST":
        # Checando se o Botão "Atualizar Valores" foi pressionado
        if "atualizar" in request.form:
            # Função para Atualizar a tabela
            w = 0
            for prods in estoque.mostrar_estoque():
                z = str(w)
                prod = Produto(request.form["numero" + z], request.form["nome" + z], request.form["preço" + z],
                            request.form["quantidade" + z], estoque.estoque)
                prod.alterar_produto(prods[0])
                w = w + 1
            # Função para Adicionar novo produto
            prodnovo = Produto(request.form["numeron"], request.form["nomen"], request.form["preçon"],
                            request.form["quantidaden"], estoque.estoque)
            prodnovo.produto_novo()
        # Função para Deletar um produto do estoque
        else:
            z = 2
            for produto in estoque.mostrar_estoque():
                y = str(z)
                #Se um botao de deletar foi pressionado
                if y in request.form:
                    del_produto = Produto(produto[0], produto[1], produto[2], produto[3], estoque.estoque)
                    del_produto.remover_produto()
                z = z + 1

    li_li_tup = Estoque.gerar_li_li_tup(estoque)
    return render_template('estoque.html', li_li_tup=li_li_tup, estoque=estoque.estoque)



@app.route("/vendas", methods=['GET','POST'])
def pag_vendas():
    if request.method == "GET":
        estoque_info = request.args.get('info')
        estoque = Estoque(estoque_info)

        #Insere a sessao na tabela de Sessoes e cria uma tabela Prod_vendidos para a sessão
        data_hora = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        sessao = Sessao(estoque_info, data_hora)
        sessao.sessao_nova()

        li_li_tup = Estoque.gerar_li_li_tup(estoque)
        
        return render_template('vendas.html', li_li_tup=li_li_tup, estoque=estoque.estoque)
                   

@app.route("/carrinho", methods=['POST'])
def pag_carrinho():
    if "carrinho" in request.form:
        # Função para enviar os produtos selecionados para o carrinho usando dicionario
        dic ={}
        li_dic = []
        s = ["numero", "nome", "preço", "quantidade"]
        z = 0
        w = 0
        val = 0
        preço = 0
        while "numero"+str(z) in request.form:
            if int(request.form["quantidade"+str(z)]) > 0 :
                for k in range(4):
                    dic[s[k]+str(w)] = request.form[s[k]+str(z)]
                    if k == 2:
                        preço = request.form[s[k]+str(z)]
                    if k == 3:
                        val = val + float(preço)*int(request.form[s[k]+str(z)])
                        preço = 0
                li_dic.append(dic)
                w = w + 1
                dic = {}
            z = z+1
        str1 = val
        str1 = str(str1).split('.', 1)[0]
        str2 = val
        str2 = str(str2).split('.', 1)[1]
        str2 = str2[0:2]
        val = str1+"."+str2
        return render_template('carrinho.html', li_dic = li_dic, estoque = request.form["nome_estoque"], subtotal = val )
    elif "reset" in request.form:
        #Recarrega a pagina para 'resetar' as quantidades selecionadas
        estoque = Estoque(request.form["nome_estoque"])
        li_li_tup = Estoque.gerar_li_li_tup(estoque)
        
        return render_template('vendas.html', li_li_tup=li_li_tup, estoque=estoque.estoque)

    elif "confirmar" in request.form:
        # Função para confirmar a venda dos produtos, retirar quantidade do estoque e adicionar na tabela _vendidos
        estoque = Estoque(request.form["nome_estoque"])
        prod_v = Prod_Vendido(0,"0",0,0,estoque.estoque)
        z = 0
        val = 0
        while "numero"+str(z) in request.form:
            prod_v.numero = request.form["numero"+str(z)]
            prod_v.nome = request.form["nome"+str(z)]
            prod_v.preço = request.form["preço"+str(z)]
            prod_v.quantidade = request.form["quantidade"+str(z)]
            prod_v.vendido()
            val = val + float(prod_v.preço)*int(prod_v.quantidade)
            z = z+1
        Sessao.adicionar_receita(estoque.estoque, val)

        li_li_tup = Estoque.gerar_li_li_tup(estoque)
        
        return render_template('vendas.html', li_li_tup=li_li_tup, estoque=estoque.estoque)
    elif "cancelar" in request.form:
        #Descarta o carrinho/Recarrega a pagina de vendas
        estoque = Estoque(request.form["nome_estoque"])
        li_li_tup = Estoque.gerar_li_li_tup(estoque)
        
        return render_template('vendas.html', li_li_tup=li_li_tup, estoque=estoque.estoque)
        
    elif "alterar" in request.form:
        estoque = Estoque(request.form["nome_estoque"])
        # Função DIFERENCIADA para criar os nomes ( começando por 0) das informações para o request_form
        # Mantem a quantidade de cada produto selecionado
        prod = str(estoque.mostrar_estoque()).translate({ord(c): '' for c in "[]()'"})
        prod = list(prod.split(","))

        li_li_tup = []
        y = []
        s = ["numero", "nome", "preço", "quantidade"]
        z = 0
        k = 0
        w = 0
        u = 0
        for info in prod:
            j = str(k)
            if "numero" + str(w) in request.form:
                if z == 0 and int(info) == int(request.form["numero" + str(w)]):
                    u = 1
            if z == 3 and u == 1:
                tup = (s[z] + j, request.form["quantidade" + str(w)])
                w = w+1
                u = 0
            elif z == 3:
                tup = (s[z] + j, 0)
            else :
                tup = (s[z] + j, info)
            y.append(tup)
            if z == 3:
                k = k + 1
                li_li_tup.append(y)
                y = []
            z = (z + 1) % 4
        
        return render_template('vendas.html', li_li_tup=li_li_tup, estoque=estoque.estoque, atualizar = True)

    elif "encerrar" in request.form:
        #Vai para a pagina de sessao_fim
        return redirect(url_for('pag_sessao_fim',info=request.form["nome_estoque"]))

@app.route("/sessao_fim", methods=['GET','POST'])
def pag_sessao_fim():
    if request.method == 'GET':
        #Finaliza a coleta de dados e apresenta o relatorio
        estoque_info = request.args.get('info')
        data_hora = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        Sessao.adicionar_hora_fim(estoque_info, data_hora)
        li_li = Sessao.get_vendidos(estoque_info)
        sess = Sessao.get_sessao(estoque_info)
        str1 = sess[0]
        str1 = str(str1).split('.', 1)[0]
        str2 = sess[0]
        str2 = str(str2).split('.', 1)[1]
        str2 = str2[0:2]
        receita = str1+"."+str2
        return render_template('sessao_fim.html', receita = receita, hora_ini = sess[1], hora_fim = sess[2], li_li = li_li, estoque = estoque_info, pagina = True)
    if request.method == 'POST':
        estoque_info = request.form["nome_estoque"]
        if "nao_salvar" in request.form:
            #Descarta o relatorio apresentado
            Sessao.fechar_sessao(estoque_info)
        if "salvar" in request.form:
            #Guarda o arquivo html da pagina(com as informações apresentadas)
            li_li = Sessao.get_vendidos(estoque_info)
            sess = Sessao.get_sessao(estoque_info)
            estoque_num = Estoque.cod_estoque(estoque_info)
            rendered = render_template('relatorio.html', receita = sess[0], hora_ini = sess[1], hora_fim = sess[2], li_li = li_li, estoque = estoque_info, estoque_num = estoque_num)
            Relatorio.guardar(estoque_info,sess[1], rendered)
            Sessao.fechar_sessao(estoque_info)
        
        return redirect(url_for('pag_estoque',info=estoque_info))

@app.route("/relatorios", methods=['GET', 'POST'])
def pag_relatorios():
    if request.method == 'GET':
        #Apresenta a lista de relatorios disponiveis 
        estoque = request.args.get("info")
        li = Relatorio.get_list(estoque)
        dic = OrderedDict()
        z = 0
        for hora in li:
            dic["rel"+str(z)] = hora[0]
            z = z+1
        return render_template('relatorios.html', dic = dic, estoque = estoque)
    if request.method == 'POST':
        #Deleta do banco o relatorio selecionado da lista
        estoque = request.form["nome_estoque"]
        li = Relatorio.get_list(estoque)
        for z in range(len(li)):
            if "rel"+str(z) in request.form:
                hora_ini = li[z]
                hora_ini = hora_ini[0]
                Relatorio.del_rel(estoque, hora_ini)

        li = Relatorio.get_list(estoque)
        dic = OrderedDict()
        z = 0
        for hora in li:
            dic["rel"+str(z)] = hora[0]
            z = z+1
        return render_template('relatorios.html', dic = dic, estoque = estoque)


@app.route("/relatorio", methods=['GET','POST'])
def pag_relatorios_rel():
    if request.method == 'GET':
        # Apresenta o arquvivo html guardado no banco
        # Se o nome do estoque tiver sido alterado depois da sessão de vendas do relatorio apresentado,
        # o nome do estoque vigente durante a sessão ainda será apresentado no relatorio,
        # visto que é o html guardado é um 'arquivo estatico' já renderizado
        estoque = request.args.get("info")
        hora_ini = request.args.get("h_ini")
        rendered = Relatorio.get_rel(estoque, hora_ini)
        return rendered
    if request.method == 'POST':
        if "baixar" in request.form:
            # Baixa no dispositivo o arquivo em formato PDF
            # Os botoes do arquivo html não aparecem no PDF pois a biblioteca FPDF não suporta a tag <input>
            hora_ini = request.form["hora_ini"]
            estoque = request.form["nome_estoque"]
            rendered = Relatorio.get_rel(estoque, hora_ini)
            hora_str = str(hora_ini).translate({ord(c): '' for c in " "})
            pdf = MyFPDF()
            pdf.add_page()
            pdf.write_html(rendered)
            response = make_response(pdf.output(dest='S').encode('latin-1'))
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = 'attachment; filename='+estoque+'_'+hora_str+'.pdf'
            return response
        if "deletar" in request.form:
            #Deleta o relatorio e volta para a pagina de relatorios
            hora_ini = request.form["hora_ini"]
            estoque = request.form["nome_estoque"]
            Relatorio.del_rel(estoque, hora_ini)
            return redirect(url_for('pag_relatorios',info=estoque))
        if "voltar" in request.form:
            #Volta para a pagina de relatorios
            estoque_num = request.form["estoque_num"]
            estoque = Estoque.get_estoque_nome(estoque_num)
            return redirect(url_for('pag_relatorios',info=estoque))



if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)