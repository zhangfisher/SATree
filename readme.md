# SATree #
TreeModel for SQLAlchemy 

基于SQLAlcemy ORM库，利用左右值原理来实现树状存储的库。

什么是左右值树存储原理可以问度娘。

SATree可以在一张数据库表中存储多棵树，并可以方便地进行树的增加、删除、移动、输出等。

树的一个节点在存储为一条记录，表现为SQLALchemy一个混合了TreeMixin的Model实例。


## 安装 ##

	
1. 通过pip进行安装

   `pip install satree`

1. 直接下载源代码，导入就可以使用


   `from satree imoport TreeMixin,TreeManager`


## 快速使用 ##

1. **SAtree只有一个源文件，直接导入就可以工作。**


     	from satree imoport TreeMixin,TreeManager
	
1. **将TreeMixin混合到SQLAlchemy Model中**

    	engine = create_engine(sqlite_uri, echo=True)
		Base = declarative_base()
		session = sessionmaker(bind=engine)()
		class User(Base, TreeMixin):
    		__tablename__ = "user"
    		id = Column(String(32), primary_key=True, default=get_uuid)
    		name = Column(String(60), default="")
    		age=Column(Integer,default=0)
    		sex=Column(Integer,default=0)
			#定义一个类属性，用来为类提供db session,
	        #如果没有定义则需要为TreeManager提供Session参数
			@property
    		def session(cls): 
        		return session
		#创建数据库表
		Base.metadata.create_all(engine)

1. **使用TreeManager管理树**

TreeManager是管理树的主要类，可以创建一个TreeManager实例来进行树节点的增加/删除/移动等操作。

	
    	tm=TreeManager(User,session)#创建一个Tree管理实例
		#创建一个根节点	
		root_node = User(name="root1")
    	tm.add_node(root_node)
		#创建一个子节点
		child_node_a=User(name="A")
    	tm.add_node(child_node_a,root_node)
		#增加为child_node_a的下一个兄弟节点
		nextsibling_node=User(name="nextsibling_node")
    	tm.add_node(nextsibling_node,child_node_a,pos=2)
		#增加为child_node_a的上一个兄弟节点
		previoussibling_node=User(name="previoussibling_node")
		tm.add_node(previoussibling_node,child_node_a,pos=3)
		#删除一个节点
		ref_node = session.query(User).filter(User.name == "B").one()
    	tm.del_node(ref_node)
		#将B节点移动到A节点下
		ref_node = session.query(User).filter(User.name == "A").one()
    	move_node = session.query(User).filter(User.name == "B").one()    	
    	tm.move_node(move_node,ref_node,pos=0)
 		#增加另一棵树
    	root_node = User(name="root2")
    	root_node.tree_id=1
    	tm.add_node(root_node)
		#保存提交到数据库
		session.commit()
		session.close()


1. **使用TreeMixin类实例方法**
	
除了使用TreeManager外，也可以直接在混合了TreeMixin的Model上使用实例方法进行操作。

	node = session.query(User).filter(User.name == "root").one()
	node.add_child(....)#增加子节点
	node.add_sibling(....)#增加兄弟节点
	node.move_to(....)#将节点移动到其他位置
	node.delete()#删除节点
    node.to_json(..)#将节点及所有子孙节点输出为json格式数据
	....

## API  ##

SATree包括：

1. **TreeManager**
	
	核心类，用来管理树存储的所有操作功能。您可以单独创建一个TreeManager实例。

		tm=TreeManager(User,session)
	初始化TreeManager实例时需要传入一个SQLAlchemy Model，并指定一个SQLAlchemy Session实例。也可以调用TreeManager.init方法。

		tm=TreeManager()
		tm.init(User,session)
		
	或者在model类中定义一个

		tm=TreeManager()
		tm.init(User)
		class User(Base, TreeMixin):
			......
			@property
    		def session(cls): 
        		return session

	TreeManager类具有提供以下方法：
	
	- **get\_nodes(tree_id=None,level=0)**
		
		用来获取节点列表

    		tree_id : 如果表中存储多棵树，则通过指定tree_id，表示返回仅返回该树节点。
			level   : 限制返回的层级，level=0时返回所有节点，level=n代表只取n级节点
    		return  ：列表值，返回所有树节点，
	- **get\_root_node(node)**
		
		获取node所在的根节点。

    		node	: 任意一个节点model实例对象
			return  ：根节点model实例
	- **get\_node\_tree_id(node)**
		
		获取node所在树的id。

    		node	: 任意一个节点model实例对象
			return  ：树的pk

	- **add\_node(,nodes, ref_node=None, pos=TREE_NODE_POSITION.LastChild,tree_id=None)**
		
		在树中增加一个或多个节点。

    		nodes	 : 要增加的混合了TreeMixin的model实例，如果是多个可以使用列表。如[node1,node2]，也支持节点数据{},如[Node1,Node2,{"name":"xxX"}].
			ref_node : 指定要增加到什么位置，如果没有指定则代表增加为根节点。
					由于一个棵树只能有一个根节点。因此当ref_node=None，则nodes包括多个节点实例时，就代表了增加了多棵树的根节点。
			pos		 : 指新增加的nodes相对于ref_node的位置。
					pos取值包括:    
						LastChild=0		:  添加为ref_node的最后一个子节点
		     			FirstChild=1	:  添加为ref_node的第一个子节点
		    			NextSibling=2	:  添加为ref_node的下一个兄弟节点
		    			PreviousSibling=3:  添加为ref_node的前一个兄弟节点
			treeid	 : 添加到指定的树中，如果没有指定，则添加到默认树中
			return   ： 无

			例：
				user=User(...)
				tm.add_node(user)
				tm.add_node([User(..),User(..),{"name":"xxx",...}])
				tm.add_node(user,ref_user,pos=2)
	- **delete\_node(node)**
		
		在树中删除一个节点，并且该节点下属的子孙节点也会被删除。

		**特别注意：**删除节点时必须通过本方法删除，一定注意不能通过SQLALchemy的delete操作或者其他数据库操作直接删除model实例，这会破坏树结构。因为该删除操作在删除model的同时需要重新计算model的左右值，这样才可以重新维护整棵树。
	- **move\_node(node,ref_node,pos=0)**
		
		将node节点移动到相对ref_node的位置，移动时会包括node下属的子孙节点一起移动。相对位置由pos值指定。
	
    		nodes	 :  要移动的节点
			ref_node :  移动的目标节点
			pos		 : 指定ref_node的相对位置。
						pos=0:移动为ref_node的最后一个子节点。
						pos=1:移动为ref_node的第一个子节点。
						pos=2:移动为ref_node的下一个节点。
						pos=3:移动为ref_node的上一个节点。
			例：
				user1=User(...)
				user2=User(...)
				tm.move_node(user1,user2,pos=0)#将user1移动到user2的最后一个子节点
				tm.move_node(user1,user2,pos=3)#将user1移动到user2的下一个子节点

	- **move\_node\_up(node,allow_upgrade=True)
move\_node\_down(node,allow_downgrade=True)
move\_node\_left(node)
		move\_node\_right(node)**
	
		这四个方法用来将节点向上、向下、向左、向右移动一个位置。该方法内部是调用move_node实现。

			node	 :  要移动的节点
			allow_upgrade：当节点是父节点的第一个节点时，是否允许升级为父节点的下一个兄弟节点。
			allow_downgrade:当节点是父节点的最后一个节点时，是否移动为上一个兄弟节点的最后兄弟节点的子节点。
	
	- **get_node_relation(node,ref_node)**

         获取节点与节点的相对关系

            node:节点实例
            ref_node：相对节点
            Return:0-两个节点相等，1-子节点，2-后代节点，3-父节点，4-祖先节点,5-兄弟节点
            例：
                n=tm.get_node_relation(node1,node2)
                n=1：说明node1是node2的子节点
        
	- **get_ancestors(node)**

         获取节点的所有祖先节点列表，包括父节点。

            node : 节点实例
			return : 节点列表
        
	- **get_parent(node)**

         获取节点的父节点。

            node : 节点实例
			return : 节点实例,如果node是根节点，则发生TreeNodeNotFound异常
        
	- **get\_ancestors_count(node)**

         获取节点的所有祖先节点的数量。

            node : 节点实例
			return : 节点数量

	- **get_descendants(node,level=0)**

         获取节点的所有子孙节点。

            node : 节点实例
			level : 限制返回的级别，0=不限制,1=只返回子节点，2=包括子孙节点，n=更多后代节点返回.
			return : 节点数量

	- **get_children(node)**

         获取节点的所有子节点,等同于get_descendants(node,level=1)。
        
	- **get\_descendants_count(node)**

         获取节点的所有子孙节点的数量。

            node : 节点实例
			return : 节点数量
	- **get\_siblings(node,include_self=False)**

         获取节点的所有兄弟节点。

            node : 节点实例
			include_self : 是否包括node自身.
			return : 节点实例列表
	- **get\_next_sibling(node)**

         获取节点的下一个兄弟节点。

            node : 节点实例
			return : 节点实例，如果node本身已经是最后一个节点了
					 则发生TreeNodeNotFound异常.
	- **get\_previous_sibling(node)**

         获取节点的上一个兄弟节点。

            node : 节点实例
			return : 节点实例，如果node本身是第一个节点了
					 则发生TreeNodeNotFound异常.
	- **is_root(node)**

         判断节点是否是根节点。

            node : 节点实例
			return : True或False

	- **get_trees()**

         获取存储在表中的树清单,树是由tree_id或__tree_key__字段来标识的。本方法是调用TreeManager.get_nodes(level=1)来获取，相当于取得所有的根节点。
            
			return : 节点列表

	- **verify\_tree(tree_id)**

        用来校验指定的树结构是否有效。该方法按照左右值存储的原理依次遍历所有tree_left,tree_right,tree_level的值来验证。
            
			return : True或False
	
	- **output(nodes=None,level=0,flatted=False,fields=[],format="json",children_name="children",pid_field_name="pId",output_err=False)**

         将树输出为JSON格式或List。

            nodes : 可以是节点实例或列表值，指定要从哪些节点开始输出，如果没有指定则输出所有Tree。
			level : 限制要输出的层次，0=不限制。
			flatted ：False时输出嵌套JSON，子节点放在children中。如:
                     [{"id":1,"tree_id":0,children:[....]},{...}...]
	                  如果True，则代表平面输出方式，按PID方式进行输出，如：
                      [{"id":1,"tree_id":0,pid:0,...},
						  {"id":1,"tree_id":0,pid:1}，
                          {...}...]
			fields： 指定要输出Model的哪些字段，如果没有指定，则输出字段由Model中定义的
					__tree_output_fields__=[...]列表来指定。
					如果没有指定__tree_output_fields__,则在Model中定义的
					__tree_node_name__=..        
					__tree_node_title__=..
					__tree_node_description=..
					__tree_node_status__=..
					__tree_node_icon__  =..
					的字段也会被输出.
					此外id,tree_id,tree_level三个字段也会输出。
			format : 输出的格式，现默认输出JSON格式，其他值输出dict
			children_name : 存放子节点的健值名称，默认值为children.
			pid_field_name : 当flatted=True时，pid字段的健名称，默认=pId.
					刚好与zTree的匹配。这样当flatted=True时，
					输出的json可以直接输出到zTree中进行加载。
			output_err:是否输出错误，当输出节点时如果出错则会在输出结果中包含错误信息.
					在调试时比较有用。
			return : JSON或Dict 


1. **TreeMixin**

TreeMixin被设计用来混合到SQLALchemy的model类中，model的每一个实例就是一个树的节点。
TreeMixin为model添加tree_id、tree_left、tree_right、tree_level四个字段。

tree_id字段用来标识节点是哪一棵树的,默认为零。如果指定__tree_key__为其他值时，则以__tree_key__字段来标识树，该字段就没有用。
tree_level指定该节点在树中的层次，比如根节点tree_level=1

**特别注意：**tree_left、tree_right、tree_level三个字段是由TreeManager自动计算维护的，不能手工进行修改，否则可能破坏树结构。

    tree_left = Column(Integer, default=0)
    tree_right = Column(Integer, default=0)
    tree_level = Column(Integer, default=0)

例：

	class User(Base, TreeMixin):
		__tablename__ = "user"
		id = Column(String(32), primary_key=True, default=get_uuid)
		name = Column(String(60), default="")
		age=Column(Integer,default=0)
		sex=Column(Integer,default=0)
        ...

TreeMixin内部会自动创建一个TreeManager的实例来进行管理树，您也可以自己在类中定义一个TreeManager的实例，如：

	class User(Base, TreeMixin):
		__tablename__ = "user"
		......
		TreeManager=myTreeManager(...)
		...


**TreeMixin的实例方法**

均是调用TreeManager的方法来实例的，节点实例提供以下方法：



- **relation_for**  :	获取节点与节点之间的关系，同TreeManager.get_node_relation。
- **add_child** 	:	增加子节点，见TreeManager.add_node。
- **add_sibling** 	:	增加兄弟节点，见TreeManager.add_node。
- **move_to** 		:	移动到新的位置，见TreeManager.add_node		
- **delete** 	:	从数据库中删除，见TreeManager.del_node
- **to_json** 	:	将自身及子孙节点输出成JSON，见TreeManager.output
- **to_list** :将自身及子孙节点输出成list，见TreeManager.output
- **move_up** :向上移动，见TreeManager.move_node_up
- **move_down** :向下移动，见TreeManager.move_node_down
- **move_left** :向左移动，见TreeManager.move_node_left
- **move_right** :向右移动，见TreeManager.move_node_right


**TreeMixin的实例属性**


- **is_root** :是否根节点，见TreeManager.is_root
- **next_sibling** :获取下一个兄弟节点，见TreeManager.add_node
- **previous_sibling** :获取上一个兄弟节点，见TreeManager.add_node
- **siblings** :获取所有兄弟节点，见TreeManager.get_siblings
- **children** :获取子节点，见TreeManager.get_children
- **parent** :获取父节点，见TreeManager.get_parent
- **ancestors** :获取祖先节点，见TreeManager.get_ancestors
- **ancestors_count** :获取祖先节点的数量，见TreeManager.get_ancestors_count
- **descendants** :获取后代节点，见TreeManager.get_descendants
- **descendants_count** :获取后代节点数量，见TreeManager.get_descendants_count


**TreeMixin的映射属性**

映射属性用来将数据库的字段映射为树节点的通用属性。这个功能主要是用来在进行output时能方便按统一的逻辑进行树的展示处理。

- **node_name** :节点名称，通过__tree_node_name__定义
- **node_title** :节点标题，通过__tree_node_title__定义
- **node_description** :节点描述，通过__tree_node_description__定义
- **node_icon** :节点图标，通过__tree_node_icon__定义
- **node_status** :节点状态，通过__tree_node_status__定义

**例：**


	class User(Base, TreeMixin):
		__tablename__ = "user"
		__tree_node_name__="fullname"
		__tree_node_icon__="sex"
		fullname = Column(String(60), default="")
		age=Column(Integer,default=0)
		sex=Column(Integer,default=0)
		...
	以下在使用output输出时，默认情况下会输出：
	[{name:"fullname的值",icon:"sex的值",......}.....]

**TreeMixin的配置项**

可以在TreeMixin类中定义以下配置属性：

- **\_\_tree_key\_\_** ：  指定用来区分别表中不同树的字段名称，默认是通过tree\_id。
- **\_\_tree_sort\_\_** ：  输出时，树的排序方式，默认是根据tree_id来排序的。
- **\_\_tree\_output_fields\_\_**=[field1,field2....]：  使用output方法时，输出哪些字段。
- **\_\_tree\_primary_key\_\_** ：声明主健字段名称，一般不需要指定，仅仅用在有双主健时。

例,如，以下用户表想按性别来分成两棵树：

	class User(Base, TreeMixin):
		__tablename__ = "user"
		__tree_key__="sex"
		name = Column(String(60), default="")
		age=Column(Integer,default=0)
		sex=Column(Integer,default=0)#取值0=男,1=女
		
	此时数据库里面自动生成的tree_id字段就没有用，TreeManager使用sex字段来区分不同的树。


