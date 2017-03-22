package readers;

import java.util.ArrayList;
import java.util.List;

import model.input.Input;
import model.output.Action;
import model.output.Defend;
import model.tree.Node;
import model.tree.Output;
import model.tree.Tree;

public class TreeReaderImpl implements TreeReader {

	private ActionReader actionReader;
	private InputReader inputReader;
	
	public TreeReaderImpl(ActionReader actionReader, InputReader inputReader) {
		setActionReader(actionReader);
		setInputReader(inputReader);
	}
	
	public InputReader getInputReader() {
		return inputReader;
	}

	public void setInputReader(InputReader inputReader) {
		this.inputReader = inputReader;
	}

	public ActionReader getActionReader() {
		return actionReader;
	}

	public void setActionReader(ActionReader actionReader) {
		this.actionReader = actionReader;
	}

	@Override
	public List<Tree> convertTrees(String gameData, int lineNumber) {
		String[] lines = gameData.split(System.lineSeparator());
		List<Tree> trees = new ArrayList<Tree>();
		boolean found = false;
		for (int i = lineNumber; i < lines.length; i++) {
			String[] values = lines[i].split("=");
			if(found && !values[0].equals("tree")) {
				return trees;
			}
			else if (values[0].equals("tree")) {
				found = true;
				Tree tree = convertTree(lines[i]);
				trees.add(tree);
			}
		}
		return trees;
	}
	
	@Override
	public Tree convertTree(String treeData) {
		treeData = treeData.substring(5);
		treeData = treeData.replace("(", "");
		treeData = treeData.replace(")", "");
		String[] temp = treeData.split(" ");
		List<String> tokens = new ArrayList<String>();
		String name = temp[0];
		Tree tree = new Tree(name);
		for (int i = 1; i < temp.length; i++) {
			tokens.add(temp[i]);
		}
		Node node = convertNode(null, tokens, tree);
		tree.setRoot(node);
		tree.setHeights();
		return tree;
	}

	private Node convertNode(Node parent, List<String> values, Tree tree) {
		switch (values.get(0)) {
		case "OUTPUT":
			values.remove(0);
			Node node = convertOutput(parent, values, tree);
			return node;
		case "BOOLEAN":
			values.remove(0);
			return convertBoolean(parent, values, tree);
		case "NUMERIC":
			values.remove(0);
			return convertNumeric(parent, values, tree);
		case "POSITION":
			values.remove(0);
			return convertPosition(parent, values, tree);
		default:
			return new Output(parent, new Defend(), tree);
		}
	}
	
	private Node convertOutput(Node parent, List<String> values, Tree tree) {
		Action action = getActionReader().readAction(values);
		return new Output(parent, action, tree);
	}

	private Node convertBoolean(Node parent, List<String> values, Tree tree) {
		int type = 2;
		List<Input> inputs = new ArrayList<Input>();
		List<Node> children = new ArrayList<Node>();
		Node node = new Node(inputs, type, children, parent, tree);
		inputs.add(convertInput(values));
		children.add(convertNode(node, values, tree));
		children.add(convertNode(node, values, tree));
		return node;
	}

	private Node convertNumeric(Node parent, List<String> values, Tree tree) {
		int type = 3;
		List<Input> inputs = new ArrayList<Input>();
		List<Node> children = new ArrayList<Node>();
		Node node = new Node(inputs, type, children, parent, tree);
		inputs.add(convertInput(values));
		inputs.add(convertInput(values));
		children.add(convertNode(node, values, tree));
		children.add(convertNode(node, values, tree));
		children.add(convertNode(node, values, tree));
		return node;
	}

	private Node convertPosition(Node parent, List<String> values, Tree tree) {
		int type = 2;
		List<Input> inputs = new ArrayList<Input>();
		List<Node> children = new ArrayList<Node>();
		Node node = new Node(inputs, type, children, parent, tree);
		inputs.add(convertInput(values));
		children.add(convertNode(node, values, tree));
		children.add(convertNode(node, values, tree));
		children.add(convertNode(node, values, tree));
		children.add(convertNode(node, values, tree));
		return node;
	}

	private Input convertInput(List<String> values) {
		return getInputReader().readInput(values);/*
		String option = values.get(0);
		if (option.equals(Option.VALUE.toString())) {
			int value = Integer.valueOf(values.get(1));
			Input input = new Input(3, Option.valueOf(option), value);
			values.remove(0);
			values.remove(0);
			return input;
		} 
		else if (isBoolean(option)) {
			Input input = new Input(2, Option.valueOf(option));
			values.remove(0);
			return input;
		} else if (isNumeric(option)) {
			Input input = new Input(3, Option.valueOf(option));
			values.remove(0);
			return input;
		} else if (isPosition(option)) {
			Input input = new Input(4, Option.valueOf(option));
			values.remove(0);
			return input;
		} else {
			Input input = new Input(1, Option.valueOf(option), -1);
			values.remove(0);
			return input;
		}*/
	}
/*
	private boolean isBoolean(String option) {
		return option.equals(Option.LEGAL_MOVE.toString()) || option.equals(Option.ENEMY_ADJACENT.toString())
				|| option.equals(Option.FOOD_ADJACENT.toString()) || option.equals(Option.LEGAL_MOVE.toString());
	}

	private boolean isNumeric(String option) {
		return option.equals(Option.CELL_HEALTH.toString()) || option.equals(Option.SQUARE_FOOD.toString())
				|| option.equals(Option.SQUARE_HEIGHT.toString()) || option.equals(Option.RANDOM.toString());
	}

	private boolean isPosition(String option) {
		return option.equals(Option.ENEMY_POSITION);
	}*/
}
