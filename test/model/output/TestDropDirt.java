package model.output;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import org.junit.After;
import org.junit.Test;

import junit.framework.TestCase;
import main.Game;
import model.Agent;
import model.Map;
import model.Tile;
import model.output.Action.Activity;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class TestDropDirt extends TestCase {

	private GameReader gameReader;
	private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();

	@Override
	protected void setUp() {
		gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		System.setOut(new PrintStream(outContent));
	}
	
	@After
	public void cleanUpStreams() {
	    System.setOut(null);
	}

	/**
	 * http://stackoverflow.com/questions/1119385/junit-test-for-system-out-println
	 */
	@Test
	public void testDropDirt_Success() {
		String file = "resources\\test\\outputMaps\\test_dropDirt_success.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int newDirt = 1;
		int prevDirt = map.getTile(agent.getCurrentPos()).getDirt();
		agent.setDirt(newDirt);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.DROP_DIRT);
		assertTrue( map.getTile(agent.getCurrentPos()).getDirt() == (prevDirt + newDirt));
	}
	
	@Test
	public void testDropDirt_Success_MaxDirt() {
		String file = "resources\\test\\outputMaps\\test_dropDirt_success_maxDirt.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int newDirt = 1;
		agent.setDirt(newDirt);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.DROP_DIRT);
		assertTrue( map.getTile(agent.getCurrentPos()).getDirt() == Tile.MAX_DIRT);
	}
	
	@Test
	public void testDropDirt_Fail_NoDirt() {
		String file = "resources\\test\\outputMaps\\test_dropDirt_fail_noDirt.map";
		String error = "Cannot DROP_DIRT because agent has no dirt\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int newDirt = 0;
		int prevDirt = map.getTile(agent.getCurrentPos()).getDirt();
		agent.setDirt(newDirt);
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.DROP_DIRT);
		assertTrue( map.getTile(agent.getCurrentPos()).getDirt() == (prevDirt + newDirt));
		assertEquals(outContent.toString(), error);
	}	
	
	@Test
	public void test_ToString() {
		DropDirt output = new DropDirt();
		String strOutput = "DROP_DIRT";
		assertTrue(output.toString().equals(strOutput));
	}
}
